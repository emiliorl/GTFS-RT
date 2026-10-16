# Transmetro (Ciudad de Guatemala) – borrador GTFS no oficial

Feed GTFS estático **no oficial** construido a partir del mapa público de la Municipalidad de Guatemala
(paradas) y las páginas de cada línea (horarios de servicio). Generado con `python build.py`.

## Frecuencias estimadas

**Las frecuencias (`frequencies.txt`) son estimadas, no oficiales.** La Municipalidad no las publica.
Valores usados: días hábiles 5 min en horas pico (06:00–09:00 y 17:00–20:00) y 10 min el resto del día;
sábados 10 min; domingos 15 min. Los tiempos de recorrido se calculan a 18 km/h + 20 s por parada.
Con los datos de operación de la Municipalidad se reemplazan directamente.

El orden de las paradas y los sentidos se tomaron de los diagramas "Estaciones de Línea N" de muniguate.com
(consultados el 2026-10-16); todas las líneas son circuitos (L1, L2, L6, L7, L12, L12E, L13, L18 y L18R). Los horarios de servicio son los de cada página de línea.

Líneas incluidas: 1, 2, 6, 7, 12, 13 y 18 (la L18 y el circuito San Rafael–Paraíso son dos circuitos que se conectan en Atlántida, estación de transbordo). Las coordenadas de las estaciones
provienen de los mapas de Google My Maps de la Municipalidad.
`shapes.txt` se genera ajustando la secuencia de paradas de cada viaje al trazado oficial de cada línea (KML de Google My Maps
en `reference/Transmetro/`, ver `shapes_lib.py`). La L12 y su expreso (Centra Sur / Trébol / Plaza El Amate) son circuitos: ida hasta Plaza El Amate y regreso por el mismo corredor (descripción del operador).
Pendiente: TuBus (rutas 5, 104, 105, 305, 402, 801 y 802): las páginas guardadas y los KML de sus mapas están en `reference/Tubus/` (ver `SOURCES.txt` allí), todavía sin convertir a GTFS.

## Datos cifrados

Por ahora los datos y el código que los genera (`build.py`, `shapes_lib.py`, `gtfs/`, el zip, los KML) **no** se publican en claro:
se guardan cifrados (AES-256) en `data.tar.gz.gpg`. `./protect.sh` cifra y `./unprotect.sh` descifra, usando la frase de
contraseña del archivo `~/.gtfs-rt-passphrase` (fuera del repositorio).

## Simulación en tiempo real (GTFS-RT)

`simulate.py` (L7 sentido La Merced) mueve buses falsos por el `shape` con la frecuencia estimada y genera `VehiclePositions` y
`TripUpdates` válidos (`--once`, `--live` cada 10 s, `--replay` para el mapa). Prueba el pipeline, no la exactitud de los datos.
`docs/` es el mapa para GitHub Pages (reproduce 30 min de feed simulado; muestra los buses y "próximo bus en N min").
Requiere `pip install -r requirements.txt`.

## Planificador de viajes (a pie + bus)

`otp/run.sh` levanta [OpenTripPlanner](https://www.opentripplanner.org/) 2.6 en local con este GTFS y el mapa de OpenStreetMap de
Guatemala (© colaboradores de OpenStreetMap, ODbL); caminar y los trasbordos entre líneas los resuelve OTP. El mapa de `docs/`
tiene un panel "Planificar viaje": se elige origen y destino sobre el mapa y se consulta `http://localhost:8080/otp/gtfs/v1`
(otro servidor con `?otp=URL`). En GitHub Pages el panel solo funciona si hay un OTP accesible; el feed no se publica.

## Carpetas de referencia

`reference/Transmetro/` (páginas de las líneas 1, 2, 6, 7, 12, 13 y 18 con sus KML) y `reference/Tubus/` (índice de TuBus, ruta 5 y rutas 104, 105, 305, 402, 801, 802 con sus KML). Son privadas: solo los KML y `SOURCES.txt` van en el archivo cifrado.
