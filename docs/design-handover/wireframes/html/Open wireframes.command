#!/bin/bash
# Double-click to view the Brahma wireframes in your browser. Close this window to stop.
cd "$(dirname "$0")"
PORT=8765
( sleep 1; open "http://localhost:$PORT/index.html" ) &
python3 -m http.server $PORT
