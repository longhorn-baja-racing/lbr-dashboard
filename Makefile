format:
	autoflake --recursive . -i --remove-all-unused-imports --ignore-init-module-imports
	isort -w 120 .
	yapf -i -r -p --style="{based_on_style: yapf, indent_width: 4, column_limit: 120}" --no-local-style ./src/
