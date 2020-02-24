# GitHub Auto-deployer
GitHub Auto-deployer using GCloud. This is a Python port of the NodeJs tutorial [Cloud Functions GitHub Auto-deployer](https://cloud.google.com/community/tutorials/cloud-functions-github-auto-deployer). View the original [source](https://github.com/GoogleCloudPlatform/community/blob/master/tutorials/cloud-functions-github-auto-deployer/auto-deployer/index.js).

### Instructions
1. Deploy the auto-deployer script
```
gcloud functions deploy github_auto_deployer --runtime python37 --trigger-http
```
2. Define config.json
