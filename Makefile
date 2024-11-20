.PHONY: clean master chunk client

clean:
	rm -rf data
	rm -rf logs
	rm -rf src/__pycache__

master:
	python run_master.py

# Updated chunk target to handle space limit
chunk:
	$(eval ID := $(word 2,$(MAKECMDGOALS)))
	$(eval SPACE := $(word 3,$(MAKECMDGOALS)))
	@if [ "$(ID)" != "" ] && [ "$(SPACE)" != "" ]; then \
		python run_chunk_server.py --id $(ID) --space $(SPACE); \
	elif [ "$(ID)" != "" ]; then \
		python run_chunk_server.py --id $(ID); \
	else \
		python run_chunk_server.py; \
	fi

client:
	streamlit run interfaces/streamlit_app.py --server.maxUploadSize 10000

# This allows arbitrary arguments to be passed
%:
	@: