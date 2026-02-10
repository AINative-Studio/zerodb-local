import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Preferences from '../../src/components/Preferences';

describe('Preferences Component', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('should render all preference sections', () => {
    render(<Preferences />);
    expect(screen.getByText('General')).toBeInTheDocument();
    expect(screen.getByText('Ports')).toBeInTheDocument();
    expect(screen.getByText('About ZeroLocal')).toBeInTheDocument();
  });

  it('should render all preference checkboxes', () => {
    render(<Preferences />);
    expect(screen.getByLabelText(/Start services automatically on login/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Show notifications/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Automatically check for updates/i)).toBeInTheDocument();
  });

  it('should render port configuration inputs', () => {
    render(<Preferences />);
    expect(screen.getByLabelText(/API Port/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Dashboard Port/i)).toBeInTheDocument();
  });

  it('should have default port values', () => {
    render(<Preferences />);
    const apiPortInput = screen.getByLabelText(/API Port/i) as HTMLInputElement;
    const dashboardPortInput = screen.getByLabelText(/Dashboard Port/i) as HTMLInputElement;
    expect(apiPortInput.value).toBe('8000');
    expect(dashboardPortInput.value).toBe('3000');
  });

  it('should update checkbox state when clicked', () => {
    render(<Preferences />);
    const checkbox = screen.getByLabelText(/Show notifications/i) as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(false);
  });

  it('should update port values when changed', () => {
    render(<Preferences />);
    const apiPortInput = screen.getByLabelText(/API Port/i) as HTMLInputElement;
    fireEvent.change(apiPortInput, { target: { value: '9000' } });
    expect(apiPortInput.value).toBe('9000');
  });

  it('should save preferences to localStorage when Save button is clicked', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    render(<Preferences />);
    const saveButton = screen.getByText('Save Preferences');
    fireEvent.click(saveButton);
    expect(setItemSpy).toHaveBeenCalledWith(
      'zerolocal-preferences',
      expect.any(String)
    );
  });

  it('should show "Saved!" text after saving', () => {
    render(<Preferences />);
    const saveButton = screen.getByText('Save Preferences');
    fireEvent.click(saveButton);
    expect(screen.getByText('Saved!')).toBeInTheDocument();
  });

  it('should load preferences from localStorage on mount', () => {
    const mockPreferences = {
      autoStartOnLogin: true,
      showNotifications: false,
      apiPort: 9000,
      dashboardPort: 4000,
      autoCheckUpdates: false,
    };
    localStorage.setItem('zerolocal-preferences', JSON.stringify(mockPreferences));

    render(<Preferences />);
    const notificationsCheckbox = screen.getByLabelText(/Show notifications/i) as HTMLInputElement;
    const apiPortInput = screen.getByLabelText(/API Port/i) as HTMLInputElement;
    expect(notificationsCheckbox.checked).toBe(false);
    expect(apiPortInput.value).toBe('9000');
  });

  it('should display version information', () => {
    render(<Preferences />);
    expect(screen.getByText(/Version 0.1.0/i)).toBeInTheDocument();
    expect(screen.getByText(/Built with Tauri, React, and Rust/i)).toBeInTheDocument();
  });

  it('should reset preferences when Reset button is clicked', () => {
    render(<Preferences />);
    const apiPortInput = screen.getByLabelText(/API Port/i) as HTMLInputElement;
    fireEvent.change(apiPortInput, { target: { value: '9000' } });
    expect(apiPortInput.value).toBe('9000');

    const resetButton = screen.getByText('Reset');
    fireEvent.click(resetButton);
    expect(apiPortInput.value).toBe('8000');
  });
});
