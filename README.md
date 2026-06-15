# Platform Automation

A dedicated repository that contains automation code for all platform features.

## Purpose

This repository serves as the central location for automation development and maintenance across the platform.

## Packages

```text
platform-automation/
├── FeatureBasedTest/ # Service-level endpoints automation
├── FlintAPITest/     # API automation scripts and helpers
├── FlintCliTest/     # CLI automation scripts and helpers
└── FlintUITest/      # UI automation scripts and helpers
```

## Package Overview

### FeatureBasedTest
Contains feature-based automation that validates platform functionality by invoking service-level endpoints.

### FlintAPITest
Contains API automation scripts, test utilities, and reusable API helpers.

### FlintCliTest
Contains CLI automation scripts, test utilities, and reusable CLI helpers.

### FlintUITest
Contains UI automation scripts, page objects, test utilities, and reusable UI helpers.

## Contribution Guidelines

- Add automation code to the appropriate package.
- Organize tests and utilities based on feature requirements.
- Follow established coding and automation standards.
- Submit changes through merge requests for review.

## Notes

- This repository serves as the single source of truth for all platform automation.
- Additional packages and automation modules can be added as the platform evolves.