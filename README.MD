# Description

This repo contains Python scripts to manage the actions I use most often with regards to AWS Lambda. Specifically, the scripts automate the following actions:

* Update a Lambda function's source code, env variables, and layers for the `$LATEST` alias.
* Publish a Lambda function to an alias or update alias's version if it already exists.
* Publish or update version of a Lambda layer.

Although these three actions are a far cry from full automation of working with Lambda, in my use case, they cover more than 90% of the interaction I have with Lambda. The usage and caveats of each script will be described below.

**_!The scripts are developed for Python-based AWS Lambda function. Lambda function written in other languages has NOT been tested!_**


# Recommended Project Layout

All the scripts are inside `scripts` folder. To use them without surprise, a project is highly recommended to be structured as follows:

```
├── lambda_functions
│   └── sample_lambda
│       ├── config.dev.json
│       ├── config.foo.json
│       ├── config.prod.json
│       └── lambda_function.py
└── scripts
    ├── __init__.py
    ├── config.py
    ├── publish_layer.py
    ├── publish_to_alias.py
    └── update_lambda.py
```

* `scripts/`: This folder holds all the scripts that handle the three AWS Lambda actions. Except from `boto3`, the scripts do NOT use any external packages.
* `lambda_functions`: This folder holds all the subfolders, each corresponding to a lambda function.
* `lambda_functions/sample_lambda`: This is an example folder for a lambda function of **the same name**. All Python code for the lambda function must live here.
* `lambda_functions/sample_lambda/config.dev.json`: This is the configuration for the development, or `$LATEST` alias, for the lambda function. It contains information for the env variables and a list of layer names. Example:
    ```json
    {
        "vars": {"env": "dev"},
        "layers": ["requests"]
    }
    ```
    The example shows that the dev version of the lambda function requires one env variable `env=dev`, and one already published layer called `requests`.
* `lambda_functions/sample_lambda/config.prod.json`: This, along with `config.foo.json`, are the configuration for each lambda alias. They only contain information about the env variables. The file layout is the same as shown above, except that there is no `"layers"` key.

# Usage

The usage described below assumes that the project layout from above is adopted.

## Update an EXISTING lambda function
The scripts **do NOT handle** the case of creating a new lambda. Thus, the initial creation of the lambda function, IAM role attachment, trigger and/or destination must be configured manually. This is the biggest caveate of these scripts.

Follow these steps to update an existing lambda function

1. Edit and test the function source code locally.
2. Create and edit the configuration of the dev (i.e. `$LATEST`) version of the function in `config.dev.json` file.
3. Use `scripts/update_lambda.py` to update the lambda function. Below is the help message of the script. See [example for function update]() for sample usage.
    ```
    ╰─$ python3 scripts/update_lambda.py -h
    usage: update_lambda.py [-h] --func_folder_path FUNC_FOLDER_PATH
                        --func_name FUNC_NAME --description DESCRIPTION

    Update lambda code and configuration for AWS Lambda Usage: env=dev
    python3 update_lambda --func_name [NAME] --func_folder_path [PATH]
    --description [DESC].

    optional arguments:
    -h, --help              show this help message and exit
    --func_folder_path FUNC_FOLDER_PATH
                            REQUIRED. The path to the folder containing one
                            or more Python files that contribute to the
                            lambda function
    --func_name FUNC_NAME
                            REQUIRED. The name of the lambda function as
                            shown on AWS.
    --description DESCRIPTION
                            REQUIRED. The description of the lambda function.
    ```

## Publish a lambda function to an alias
Except from the word `dev`, there is no restriction on alias name. The reason `dev` is forbidden for alias name is to ensure that the function for dev is always tied to `$LATEST` version.

Follow these steps to publish to alias

1. Create and edit the configuration for the alias in `config.[alias].json` file.
2. Use `scripts/publish_to_alias.py` to publish the alias. Below is the help message of the script. See [example for alias publication]() for sample usage.
    ```
    ╰─$ python3 scripts/publish_to_alias.py -h
    usage: publish_to_alias.py [-h] --func_folder_path FUNC_FOLDER_PATH
                            --func_name FUNC_NAME --alias ALIAS
                            --description DESCRIPTION

    Publish a new version of the well-tested lambda function, and assign an
    alias to it. When publishing a new version, the only thing that needs to
    be updated is the environmental variable. Usage: python3 publish_to_alias
    --func_folder_path [path] --func_name [lambda name] --alias [alias]
    --description [description of the alias].

    optional arguments:
    -h, --help            show this help message and exit
    --func_folder_path FUNC_FOLDER_PATH
                            REQUIRED. The path to the folder containing
                            configs for lambda function of different alias
    --func_name FUNC_NAME
                            REQUIRED. The name of the lambda function as
                            shown on AWS.
    --alias ALIAS           REQUIRED. Name of the alias.
    --description DESCRIPTION
                            REQUIRED. The description of the lambda function
                            version used forthe alias.

    ```

## Publish a layer
Layer is a way for different lambda functions to share the same resources. Typically, one uploads a third-party package not offered by AWS Lambda's Python runtime as a layer, such that more than one lambda functions can import and use that package and there is no need to include that package in the lambda source code.

For more information about layers, check out its [documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html).

Use `scripts/publish_layer.py` to publish a layer. Below is the help message of the scripts. See [example for layer publication]() for sample usage.

    ```
    ╰─$ python3 scripts/publish_layer.py -h
    usage: publish_layer.py [-h] --package_name PACKAGE_NAME --description
                            DESCRIPTION

    Publish a layer to AWS Lambda. A layer is a package that is shared and
    can be imported by all Lambda under the same account If the layer name
    never exists before, create a new one. If it already exists, update it to
    a new version. Note that layer name must be the same as package
    nameUsage: python3 publish_layer --package_name [PACKAGE
    NAME]--description [DESC].

    optional arguments:
    -h, --help              show this help message and exit
    --package_name PACKAGE_NAME
                            REQUIRED. Name of the package to be uploaded as a
                            layer.
    --description DESCRIPTION
                            REQUIRED. Description of the latest version of
                            the layer.
    ```

### Caveat
The method for publishing layer borrows from [this post](https://aws.amazon.com/premiumsupport/knowledge-center/lambda-import-module-error-python/). However, there is one major difference: in the post, the package is installed on AWS EC2. This is important because not all Python packages work across all platforms. For instance, since I am on macOS, when I use `scripts/publish_layer.py`, the published layer contains the package specifically installed for macOS. AWS Lambda function runs on Amazon Linux. If the Python package for macOS is compatible with Amazon Linux (e.g. `requests`), then our published layer works. However, if the Python package for macOS is not compatible with Amazon Linux (e.g. `scikit-learn`), one must install and publish the layer from an EC2 instance.

Overall, this shouldn't be too big an issue, because the amount of times one need to publish layer is much lower than update lambda function source code or publish to an alias.


# Example

This repo contains a sample lambda function to demonstrate how the scripts work. Follow the steps below to see for yourself.

1. Clone the repo
    ```bash
    git clone ??
    ```
2. Create a virtualenv for `aws_lambda_scripts`.
3. Install dependencies
    ```bash
    pip install -r requirements.txt
    ```
4. Configure credentials for `boto3`. I recommend setting environment variables to specify which credentials to use ([documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#environment-variables)). For example, I export `AWS_PROFILE=default` to the shell to ensure that all lambda actions happen to my default AWS account.
5. Create a lambda function called `sample_lambda` on AWS. Assign it basic Lambda function execution role.
6. Publish a layer for the package `requests`. This external package will be used by the lambda function
    ```bash
    python3 scripts/publish_layer.py \
        --package_name requests \
        --description "A layer to use requests"
    ```
7. Update lambda function (alternatively, use `make update_sample_lambda`)
    ```bash
    env=dev python3 scripts/update_lambda.py \
        --func_folder_path lambda_functions/sample_lambda \
        --func_name sample_lambda \
        --description "A lambda function for demo purpose"
    ```
    After update is successful, go to AWS console, test the function, and examine the output.
8. Publish the lambda function to `prod` alias (alternatively, use `make publish_sample_lambda_to_prod`)
    ```bash
    python3 scripts/publish_to_alias.py \
		--func_folder_path lambda_functions/sample_lambda \
		--func_name sample_lambda \
		--alias prod \
		--description "Alias for production"
    ```
    After publication is successful, go to AWS console, inspect the `prod` alias, test the alias, and examine the output. Compared to the output from the `$LATEST` version, one shall see the difference in the env variable value.
9. (Optional) Publish the lambda function to another alias called `foo` (alternatively, use `make publish_sample_lambda_to_foo`)
    ```bash
    python3 scripts/publish_to_alias.py \
		--func_folder_path lambda_functions/sample_lambda \
		--func_name sample_lambda \
		--alias foo \
		--description "Just some random alias"
    ```
    Inspect and test the `foo` alias the same way as before.

