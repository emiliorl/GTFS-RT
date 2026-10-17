#!/usr/bin/env bash
# Local OpenTripPlanner for the Transmetro draft feed: downloads OTP + Guatemala OSM if missing, builds the graph when the
# feed changed, then serves GraphQL at http://localhost:8080/otp/gtfs/v1 (the map's trip planner calls it).
# Needs Java 21+, ~6 GB RAM, and ../transmetro_gtfs_draft.zip (run ./unprotect.sh first if it is missing).
set -euo pipefail
cd "$(dirname "$0")"
OTP_VERSION=2.6.0
JAR="otp-$OTP_VERSION-shaded.jar"
mkdir -p data
[ -f "$JAR" ] || curl -L -o "$JAR" "https://repo1.maven.org/maven2/org/opentripplanner/otp/$OTP_VERSION/$JAR"
[ -f data/guatemala.osm.pbf ] || curl -L -o data/guatemala.osm.pbf https://download.geofabrik.de/central-america/guatemala-latest.osm.pbf
cp config/*.json data/
cp ../transmetro_gtfs_draft.zip data/transmetro-gtfs.zip
[ -f ../tubus_gtfs_draft.zip ] && cp ../tubus_gtfs_draft.zip data/tubus-gtfs.zip || true
[ -f ../express_gtfs_draft.zip ] && cp ../express_gtfs_draft.zip data/express-gtfs.zip || true
if [ ! -f data/graph.obj ] || [ data/transmetro-gtfs.zip -nt data/graph.obj ] || [ -f data/tubus-gtfs.zip -a data/tubus-gtfs.zip -nt data/graph.obj ] || [ -f data/express-gtfs.zip -a data/express-gtfs.zip -nt data/graph.obj ] || [ config/build-config.json -nt data/graph.obj ]; then
  java -Xmx8G -jar "$JAR" --build --save data
fi
exec java -Xmx6G -jar "$JAR" --load --serve data
