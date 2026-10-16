# Transmetro (Ciudad de Guatemala) – borrador GTFS no oficial

Feed GTFS estático **no oficial** construido a partir del mapa público de la Municipalidad de Guatemala
(paradas) y las páginas de cada línea (horarios de servicio). Generado con `python build.py`.

## Frecuencias estimadas

**Las frecuencias (`frequencies.txt`) son estimadas, no oficiales.** La Municipalidad no las publica.
Valores usados: días hábiles 5 min en horas pico (06:00–09:00 y 17:00–20:00) y 10 min el resto del día;
sábados 10 min; domingos 15 min. Los tiempos de recorrido se calculan a 18 km/h + 20 s por parada.
Con los datos de operación de la Municipalidad se reemplazan directamente.

El orden de las paradas y los sentidos se tomaron de los diagramas "Estaciones de Línea N" de muniguate.com
(consultados el 2026-10-16); L1, L2 y L13 son circulares. Los horarios de servicio son los de cada página de línea.

Líneas incluidas: 1, 2, 6, 7, 12, 13 y 18 (más el circuito San Rafael–Paraíso de la L18). Las coordenadas de las estaciones
provienen de los mapas de Google My Maps de la Municipalidad.
`shapes.txt` se genera ajustando la secuencia de paradas de cada viaje al trazado oficial de cada línea (KML de Google My Maps
en `reference/`, ver `shapes_lib.py`). El servicio expreso de la L12 (Centra Sur / Trébol / Plaza El Amate) se modela en ambos
sentidos dentro de los horarios publicados, porque la Municipalidad no indica el sentido: es un supuesto.
Pendiente: ruta 5 (TuBus).

## Datos cifrados

Por ahora los datos y el código que los genera (`build.py`, `shapes_lib.py`, `gtfs/`, el zip, los KML) **no** se publican en claro:
se guardan cifrados (AES-256) en `data.tar.gz.gpg`. `./protect.sh` cifra y `./unprotect.sh` descifra, usando la frase de
contraseña del archivo `~/.gtfs-rt-passphrase` (fuera del repositorio).
