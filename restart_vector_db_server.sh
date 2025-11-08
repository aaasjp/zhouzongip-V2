#!/bin/bash
kill -9 $(ps aux | grep "python vector_db_server.py" | grep -v grep | awk '{print $2}')
nohup python vector_db_server.py >>logs/vector_db_server.log 2>&1 &
