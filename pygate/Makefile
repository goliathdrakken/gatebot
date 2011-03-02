PYTHON_TOP = $(shell dirname $(shell pwd))
PYTHON_ENV = PYTHONPATH=$(PYTHON_TOP)

ADMIN_COMMAND = gate-admin.py

SETUP_LOGFILE = $(PYTHON_TOP)/pygate/setup.log

setup: install_db admin

install_db:
	@echo "--- Logging to: $(SETUP_LOGFILE)"
	@echo "--- Installing database ..."
	@$(ADMIN_COMMAND) kb_setup >> $(SETUP_LOGFILE)

admin:
	@echo "--- Creating super user ..."
	@$(ADMIN_COMMAND) createsuperuser

sync_and_migrate:
	@echo "--- Syncing and migrating"
	@$(ADMIN_COMMAND) syncdb
	@$(ADMIN_COMMAND) migrate --all

clean:
	rm -f kegbot.log $(SETUP_LOGFILE)
	rm -rf build dist src/gatebot.egg-info
	find . -name "*.pyc" | xargs rm -f

distclean: clean fixtures_clean
	rm -f pygate.sqlite.bin
	rm -f pygate.sqlite.bin-journal
	for f in $(hg status -ni .); do rm -i $f; done

test:
	@echo "--- Running all tests"
	@$(ADMIN_COMMAND) test --exe -i ".*_test" pygate
# Extra args for coverage:
# --with-coverage --cover-package=pygate --cover-html \
# --cover-html-dir=buid/coverage 

### These targets are obsolete or rarely used

fixtures: distclean test
	$(ADMIN_COMMAND) dumpdata $(PROD_ADMIN_ARGS) --format=json > core/fixtures/initial_data.json

fixtures_clean:
	rm -f core/fixtures/initial_data.json

.PHONY: setup install_db admin clean distclean test sync_and_migrate
.PHONY: testdata fixtures fixtures_clean

# vim: noet
