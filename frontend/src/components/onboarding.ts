export class OnboardingPortal {
  private currentStep = 1;
  private totalSteps = 4;

  constructor() {
    this.initEventListeners();
  }

  private initEventListeners() {
    // Navigation toggle between Landing & Onboarding
    const launchOnboardingBtn = document.getElementById('btn-launch-onboarding');
    const heroOnboardingBtn = document.getElementById('btn-hero-onboarding');
    const enterSimBtn = document.getElementById('btn-enter-sim');
    const directSimBtn = document.getElementById('btn-direct-sim');
    const headerGuideBtn = document.getElementById('btn-header-guide');

    launchOnboardingBtn?.addEventListener('click', () => this.showOnboarding());
    heroOnboardingBtn?.addEventListener('click', () => this.showOnboarding());
    headerGuideBtn?.addEventListener('click', () => this.showOnboarding());

    enterSimBtn?.addEventListener('click', () => this.closePortal());
    directSimBtn?.addEventListener('click', () => this.closePortal());

    // Stepper navigation buttons
    document.getElementById('btn-next-step')?.addEventListener('click', () => this.nextStep());
    document.getElementById('btn-prev-step')?.addEventListener('click', () => this.prevStep());

    // Allow clicking step nodes directly
    for (let i = 1; i <= this.totalSteps; i++) {
      const node = document.getElementById(`step-node-${i}`);
      node?.addEventListener('click', () => this.goToStep(i));
    }
  }

  public showPortal() {
    const portal = document.getElementById('portal-overlay');
    if (portal) portal.classList.remove('hidden');
  }

  public showOnboarding() {
    this.showPortal();
    const landingView = document.getElementById('landing-view');
    const onboardingView = document.getElementById('onboarding-view');
    if (landingView && onboardingView) {
      landingView.style.display = 'none';
      onboardingView.style.display = 'block';
    }
    this.goToStep(1);
  }

  public showLanding() {
    this.showPortal();
    const landingView = document.getElementById('landing-view');
    const onboardingView = document.getElementById('onboarding-view');
    if (landingView && onboardingView) {
      landingView.style.display = 'block';
      onboardingView.style.display = 'none';
    }
  }

  public closePortal() {
    const portal = document.getElementById('portal-overlay');
    if (portal) portal.classList.add('hidden');
  }

  private goToStep(step: number) {
    if (step < 1 || step > this.totalSteps) return;
    this.currentStep = step;

    // Update slides
    for (let i = 1; i <= this.totalSteps; i++) {
      const slide = document.getElementById(`step-slide-${i}`);
      const node = document.getElementById(`step-node-${i}`);
      if (slide) {
        slide.classList.toggle('active', i === step);
      }
      if (node) {
        node.classList.toggle('active', i === step);
        node.classList.toggle('completed', i < step);
      }
    }

    // Update progress fill bar
    const fill = document.getElementById('stepper-line-fill');
    if (fill) {
      const percent = ((step - 1) / (this.totalSteps - 1)) * 100;
      fill.style.width = `${percent}%`;
    }

    // Update buttons
    const prevBtn = document.getElementById('btn-prev-step') as HTMLButtonElement;
    const nextBtn = document.getElementById('btn-next-step') as HTMLButtonElement;
    const finishBtn = document.getElementById('btn-finish-onboarding') as HTMLButtonElement;

    if (prevBtn) prevBtn.style.visibility = step === 1 ? 'hidden' : 'visible';
    if (nextBtn) nextBtn.style.display = step === this.totalSteps ? 'none' : 'inline-flex';
    if (finishBtn) finishBtn.style.display = step === this.totalSteps ? 'inline-flex' : 'none';
  }

  private nextStep() {
    if (this.currentStep < this.totalSteps) {
      this.goToStep(this.currentStep + 1);
    }
  }

  private prevStep() {
    if (this.currentStep > 1) {
      this.goToStep(this.currentStep - 1);
    }
  }
}
