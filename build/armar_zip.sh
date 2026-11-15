#!/bin/sh
# Arma entrega/TP5_Entrega.zip: el documento del desarrollo (PDF) y el prototipo sin dependencias ni artefactos (desde TP5/)
set -e
rm -rf entrega/tmp entrega/TP5_Entrega.zip
mkdir -p entrega/tmp/TP5_Entrega
cp docs/TP5_Desarrollo.pdf entrega/tmp/TP5_Entrega/
rsync -a --exclude node_modules --exclude /prototipo/artifacts --exclude /prototipo/cache --exclude coverage --exclude coverage.json --exclude .env --exclude /prototipo/despliegue.json prototipo entrega/tmp/TP5_Entrega/
(cd entrega/tmp && zip -qr ../TP5_Entrega.zip TP5_Entrega -x '*.DS_Store')
rm -rf entrega/tmp
unzip -l entrega/TP5_Entrega.zip
