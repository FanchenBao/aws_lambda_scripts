# Usage: make update_sample_lambda
update_sample_lambda:
	env=dev python3 scripts/update_lambda.py \
		--func_folder_path lambda_functions/sample_lambda \
		--func_name sample_lambda \
		--description "A lambda function for demo purpose"

# Usage; make publish_sample_lambda_to_prod
publish_sample_lambda_to_prod:
	python3 scripts/publish_to_alias.py \
		--func_folder_path lambda_functions/sample_lambda \
		--func_name sample_lambda \
		--alias prod \
		--description "Alias for production"

# Usage; make publish_sample_lambda_to_foo
publish_sample_lambda_to_foo:
	python3 scripts/publish_to_alias.py \
		--func_folder_path lambda_functions/sample_lambda \
		--func_name sample_lambda \
		--alias foo \
		--description "Just some random alias"