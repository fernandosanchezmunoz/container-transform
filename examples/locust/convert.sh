cat docker-compose.yml | \
docker run --rm -i micahhausler/container-transform -o marathon > \
output.marathon.json
