
PHONY: coverage.xml
coverage: check-python-venv
	@echo "Running tests under coverage for $(appname_verbose) …"
	@coverage run -m pytest --ignore=tests nextcloud_contacts_to_gequdio; \
	coverage xml -o coverage.xml; \
	coverage html -d htmlcov; \
	coverage report -m

# Help
.PHONY: help
help::
	@echo "  $(TEXT_UNDERLINE)Tests:$(TEXT_UNDERLINE_END)"
	@echo "    coverage                    Run tests and create a coverage report"
	@echo ""
