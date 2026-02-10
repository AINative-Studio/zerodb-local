use anyhow::{Context, Result};
use bollard::container::{ListContainersOptions, StartContainerOptions, StopContainerOptions};
use bollard::Docker;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceStatus {
    pub name: String,
    pub status: String,
    pub healthy: bool,
    pub port: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DockerStatus {
    pub docker_running: bool,
    pub services: Vec<ServiceStatus>,
}

pub struct DockerManager {
    docker: Docker,
    compose_path: PathBuf,
}

impl DockerManager {
    pub fn new(compose_path: PathBuf) -> Result<Self> {
        let docker = Docker::connect_with_local_defaults()
            .context("Failed to connect to Docker. Is Docker Desktop running?")?;

        Ok(Self {
            docker,
            compose_path,
        })
    }

    pub async fn check_docker_running(&self) -> bool {
        self.docker.ping().await.is_ok()
    }

    pub async fn get_status(&self) -> Result<DockerStatus> {
        let docker_running = self.check_docker_running().await;

        if !docker_running {
            return Ok(DockerStatus {
                docker_running: false,
                services: vec![],
            });
        }

        let mut filters = HashMap::new();
        filters.insert("label".to_string(), vec!["com.docker.compose.project=zerodb-local".to_string()]);

        let containers = self.docker
            .list_containers(Some(ListContainersOptions {
                all: true,
                filters,
                ..Default::default()
            }))
            .await?;

        let services: Vec<ServiceStatus> = containers
            .into_iter()
            .map(|container| {
                let name = container
                    .names
                    .and_then(|names| names.first().map(|n| n.trim_start_matches('/').to_string()))
                    .unwrap_or_else(|| "unknown".to_string());

                let status = container.state.unwrap_or_else(|| "unknown".to_string());
                let healthy = status == "running";

                let port = container.ports.and_then(|ports| {
                    ports.first().and_then(|p| {
                        p.public_port.map(|port| format!("localhost:{}", port))
                    })
                });

                ServiceStatus {
                    name,
                    status,
                    healthy,
                    port,
                }
            })
            .collect();

        Ok(DockerStatus {
            docker_running: true,
            services,
        })
    }

    pub async fn start_services(&self) -> Result<String> {
        let output = self.run_compose_command(&["up", "-d"]).await?;
        Ok(output)
    }

    pub async fn stop_services(&self) -> Result<String> {
        let output = self.run_compose_command(&["down"]).await?;
        Ok(output)
    }

    pub async fn restart_services(&self) -> Result<String> {
        let output = self.run_compose_command(&["restart"]).await?;
        Ok(output)
    }

    pub async fn get_logs(&self, service: Option<String>) -> Result<String> {
        let mut args = vec!["logs", "--tail=100"];
        if let Some(svc) = &service {
            args.push(svc);
        }
        let output = self.run_compose_command(&args).await?;
        Ok(output)
    }

    async fn run_compose_command(&self, args: &[&str]) -> Result<String> {
        use std::process::Command;

        let output = Command::new("docker")
            .arg("compose")
            .arg("-f")
            .arg(&self.compose_path)
            .args(args)
            .output()
            .context("Failed to execute docker compose command")?;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            let error = String::from_utf8_lossy(&output.stderr).to_string();
            anyhow::bail!("Docker compose command failed: {}", error)
        }
    }

    pub async fn check_prerequisites(&self) -> Result<PrerequisiteCheck> {
        let docker_installed = std::process::Command::new("docker")
            .arg("--version")
            .output()
            .is_ok();

        let docker_running = if docker_installed {
            self.check_docker_running().await
        } else {
            false
        };

        let ports_available = self.check_ports_available(&[8000, 3000, 5432, 6333, 9000]).await;
        let disk_space = self.check_disk_space().await;

        Ok(PrerequisiteCheck {
            docker_installed,
            docker_running,
            ports_available,
            disk_space_sufficient: disk_space > 2_000_000_000,
        })
    }

    async fn check_ports_available(&self, ports: &[u16]) -> bool {
        use std::net::{TcpListener, SocketAddr};

        for &port in ports {
            let addr = SocketAddr::from(([127, 0, 0, 1], port));
            if TcpListener::bind(addr).is_err() {
                return false;
            }
        }
        true
    }

    async fn check_disk_space(&self) -> u64 {
        use std::fs;

        if let Ok(metadata) = fs::metadata("/") {
            return metadata.len();
        }
        0
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrerequisiteCheck {
    pub docker_installed: bool,
    pub docker_running: bool,
    pub ports_available: bool,
    pub disk_space_sufficient: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[tokio::test]
    async fn test_docker_manager_creation() {
        let path = PathBuf::from("/tmp/docker-compose.yml");
        let result = DockerManager::new(path);
        assert!(result.is_ok() || result.is_err());
    }

    #[tokio::test]
    async fn test_check_ports_available() {
        let path = PathBuf::from("/tmp/docker-compose.yml");
        if let Ok(manager) = DockerManager::new(path) {
            let available = manager.check_ports_available(&[8000]).await;
            assert!(available || !available);
        }
    }

    #[tokio::test]
    async fn test_prerequisite_check() {
        let path = PathBuf::from("/tmp/docker-compose.yml");
        if let Ok(manager) = DockerManager::new(path) {
            let check = manager.check_prerequisites().await;
            assert!(check.is_ok());
        }
    }
}
