# GitHub Actions: Reusable Workflows

This repository contains several reusable GitHub Actions designed to automate common CI/CD tasks. Each action is self-contained and can be integrated into your workflows to streamline processes such as reporting test results, deploying sites, and preparing documentation.

## Actions Overview

### 1. allure-report-with-history
Generates Allure test reports with history support. Use this action to publish test results with historical trends. This action generates an Allure report and preserves the history of previous runs. It sets up Java, installs the Allure CLI, and downloads previous report history for trend analysis.

**Usage Example:**
```yaml
- name: Generate Allure Report
  uses: NayeemJohnY/actions/allure-report-with-history@main
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    allure-results-dir: test-results/allure-results
    allure-report-dir: test-results/allure-report
```

### 2. prepare-github-pages
Prepares files and configuration for deploying to GitHub Pages. Use this before deploying your site. This action copies Allure reports and optionally Javadoc to the GitHub Pages directory for deployment.

**Usage Example:**
```yaml
- name: Prepare GitHub Pages
  uses: NayeemJohnY/actions/prepare-github-pages@main
  with:
    allure-report-dir: test-results/allure-report
    playwright-report-dir: ./playwright-report # Optional
    test-results-json: test-results/test-results-report.json # Optional
    javadoc-dir: ./target/site/apidocs  # Optional
    output-dir: github-pages  # Optional, defaults to github-pages
```

### 3. deploy-github-pages-site
Deploys a static site to GitHub Pages. Ideal for publishing documentation or web apps. This action sets up GitHub Pages, uploads artifacts from the `github-pages/` directory, and publishes the site.

**Usage Example:**
```yaml
- name: Deploy to GitHub Pages
  uses: NayeemJohnY/actions/deploy-github-pages-site@main
```
### 4. post-test-results-to-azure-devops
Posts test results to Azure DevOps using a Python script. Useful for integrating GitHub Actions with Azure DevOps pipelines. This action sets up Python, installs dependencies, and executes a script to post test results to your Azure DevOps Test Plan.

**Usage Example:**
```yaml
- name: Post Test Results to Azure DevOps
  uses: NayeemJohnY/actions/post-test-results-to-azure-devops@main
  with:
    test-results-json: test-results-report.json
    azure-token: ${{ secrets.AZURE_TOKEN }}
    org-url: ${{ secrets.AZURE_ORG_URL }}
    project: ${{ secrets.AZURE_PROJECT }}
```
### Sample Test Results JSON for Azure DevOps Action
Below is a sample `test-results-report.json` required for the `post-test-results-to-azure-devops` action:
```json
{
  "testResults": {
    "22": {
      "outcome": "Passed",
      "comment": "Automated Test Name: testShouldRejectBookCreationWithClientProvidedId",
      "durationInMs": 3246,
      "errorMessage": "",
      "iterationDetails": [
        {
          "id": 1,
          "outcome": "Passed",
          "comment": "Initial Attempt",
          "durationInMs": 3246,
          "errorMessage": ""
        }
      ]
    }
  },
  "testPlanName": "Automation Test Plan",
  "testSuiteName": "Book API RestAssured Automation Test Suite"
}
```

## How to Use These Actions

1. Reference the action in your workflow using the `uses` keyword and the full repository path as shown in the examples above.
2. Replace `NayeemJohnY/actions` with your fork or the public repository path if needed.
3. Provide required inputs as specified in each action's `action.yml` file.

### Combining Actions
You can combine these actions to build powerful, automated workflows. For example:
```yaml
jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Run your tests here...
      
      - name: Prepare GitHub Pages
        uses: NayeemJohnY/actions/prepare-github-pages@main
        with:
          reports-dir: ./allure-results
          
      - name: Generate Allure Report
        uses: NayeemJohnY/actions/allure-report-with-history@main
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Deploy to GitHub Pages
        uses: NayeemJohnY/actions/deploy-github-pages-site@main
```

---
For detailed input and output options, refer to each action's `action.yml` file.
