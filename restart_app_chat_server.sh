#!/bin/bash
kill -9 $(ps aux | grep "python app_chat_server.py" | grep -v grep | awk '{print $2}')
nohup python app_chat_server.py >>logs/app_chat_server.log 2>&1 &
