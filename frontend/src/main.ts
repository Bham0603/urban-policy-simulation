import './style.css';
import { DashboardApp } from './components/dashboard';
import { OnboardingPortal } from './components/onboarding';

// Initialize the Premium Simulation Dashboard App & Landing/Onboarding Portal
window.addEventListener('DOMContentLoaded', () => {
  try {
    (window as any).app = new DashboardApp();
    (window as any).portal = new OnboardingPortal();
  } catch (error) {
    console.error("Failed to initialize Pravaah Dashboard App:", error);
  }
});
