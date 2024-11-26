.PHONY: clean master chunk client

clean:
	rm -rf data
	rm -rf logs
	rm -rf src/__pycache__

master:
	python run_master.py

# Updated chunk target to handle location coordinates
chunk:
	$(eval ID := $(word 2,$(MAKECMDGOALS)))
	$(eval X := $(word 3,$(MAKECMDGOALS)))
	$(eval Y := $(word 4,$(MAKECMDGOALS)))
	$(eval SPACE := $(word 5,$(MAKECMDGOALS)))
	@if [ "$(ID)" != "" ] && [ "$(X)" != "" ] && [ "$(Y)" != "" ] && [ "$(SPACE)" != "" ]; then \
		python run_chunk_server.py configs/config.toml --server_id $(ID) --x $(X) --y $(Y) --space $(SPACE); \
	elif [ "$(ID)" != "" ] && [ "$(X)" != "" ] && [ "$(Y)" != "" ]; then \
		python run_chunk_server.py configs/config.toml --server_id $(ID) --x $(X) --y $(Y); \
	elif [ "$(ID)" != "" ]; then \
		python run_chunk_server.py configs/config.toml --server_id $(ID); \
	else \
		python run_chunk_server.py configs/config.toml; \
	fi

# Updated client target to handle location coordinates
client:
	$(eval ID := $(word 2,$(MAKECMDGOALS)))
	$(eval X := $(word 3,$(MAKECMDGOALS)))
	$(eval Y := $(word 4,$(MAKECMDGOALS)))
	@if [ "$(ID)" != "" ] && [ "$(X)" != "" ] && [ "$(Y)" != "" ]; then \
		python run_client.py --client_id $(ID) --x $(X) --y $(Y); \
	elif [ "$(ID)" != "" ]; then \
		python run_client.py --client_id $(ID); \
	else \
		python run_client.py; \
	fi

# This allows arbitrary arguments to be passed
%:
	@: