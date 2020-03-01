# github_auto_deployer
Automatically deploy [HTTP Cloud Functions](https://cloud.google.com/functions/docs/writing/http) using [GitHub Webhooks](https://developer.github.com/webhooks/) and the HTTP Cloud Function `github_auto_deployer`. This tool is a Python port of the NodeJs community tutorial [Cloud Functions GitHub Auto-deployer](https://cloud.google.com/community/tutorials/cloud-functions-github-auto-deployer). View the original [source code](https://github.com/GoogleCloudPlatform/community/blob/master/tutorials/cloud-functions-github-auto-deployer/auto-deployer/index.js).

## Prerequisites
- Create a project in the [Google Cloud Platform Console](https://console.cloud.google.com/)
- Enable billing for your project
- Install the [Google Cloud SDK](https://cloud.google.com/sdk)

## Deploying github_auto_deployer
1. Clone or dowload this repository
2. Define your `config.json` file
```json
{
  "autoDeployer": {
    "stagingBucket": "STORAGE BUCKET NAME",
    "githubSecretToken": "GITHUB SECRET TOKEN",
    "projectId": "PROJECT ID"
  },
  "deployments": [
    {
      "repositoryName": "GITHUB REPOSITORY NAME",
      "cloudFunction": {
        "location": "LOCATION (aka REGION)",
        "name": "NAME",
        "runtime": "SUPPORTED LANGUAGE RUNTIME"
      }
    }
  ]
}
```
where
- `STORAGE BUCKET NAME` is the Cloud Storage bucket you want `github_auto_deployer` to use for uploading archives
- `GITHUB SECRET TOKEN` is a random string used to limit requests to those coming from GitHub Webhooks. Read [Securing your webhooks](https://developer.github.com/webhooks/securing/) for more information.
- `PROJECT ID` is the project you'll be using to deploy `github_auto_deployer`. Learn more about [Google Cloud projects](https://cloud.google.com/storage/docs/projects).
- `deployments` is a list of repositories that will utilize `github_auto_deployer` to trigger auto-deployments. Learn more about [Google Cloud Function concepts](https://cloud.google.com/functions/docs/concepts) to determine valid values for `location`, `name`, and `runtime`.

3. Run the following command to deploy `github_auto_deployer`:
```
gcloud functions deploy github_auto_deployer --runtime python37 --trigger-http
```

## Enabling Auto-deploy on a Repository
Read [Creating Webhooks](https://developer.github.com/webhooks/creating/) for an overview on how to setup a webhook.

tl;dr
- Run `gcloud functions describe github_auto_deployer --region=us-central1 | grep 'url'` to get the Payload URL
- Set Content type to `application/json`
- Set Secret to the `GITHUB SECRET TOKEN` value from your `config.json` file
- Only the `push event` should be used to trigger the webhook

## Disclaimers
1. I have only tested `github_auto_deployer` on tiny repositories and runs within the 60s Cloud Function default timeout. You might want to increase the timeout value on larger repositories.

2. You will see a `Service Timeout` from your webhook. Why? "GitHub expects that integrations respond within 10 seconds of receiving the webhook payload. If your service takes longer than that to complete, then GitHub terminates the connection and the payload is lost." ([Favour asynchronous work over synchronous](https://developer.github.com/v3/guides/best-practices-for-integrators/#favor-asynchronous-work-over-synchronous)). Although GitHub terminates the connection, `github_auto_deployer` continues execution as normal.



## Personal Notes
Links that helped me port this
- https://gist.github.com/categulario/deeb41c402c800d1f6e6
- http://googleapis.github.io/google-api-python-client/docs/dyn/cloudfunctions_v1.html
- https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/compute/api/create_instance.py#L128-L142
