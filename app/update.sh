   #!/bin/bash
   cd /app
   git fetch origin
   git reset --hard origin/main
   pip install --no-cache-dir -r requirements.txt
   touch /app/tmp/needs_restart
   echo "Update abgeschlossen"