#  --- GMT defaults
gmt set PS_MEDIA A2  PROJ_LENGTH_UNIT cm    FONT_TITLE 18p    FONT_LABEL 12p  
#gmtset ANOT_FONT_SIZE 10p    

#########
PHASE=P
#########

echo PHASE: ${PHASE}

MODEL=ak135
echo MODEL: ${MODEL}
OUTPATH=./${MODEL}
echo OUTPATH: ${OUTPATH}

DATAFILE0=${OUTPATH}/${MODEL}.${PHASE}.DEFAULT.time
PSFILE=${DATAFILE0}.ps
DATAFILE=${DATAFILE0}.buf

CPTFILE=${DATAFILE0}.cpt
gmt makecpt -T0/2500/50 > ${CPTFILE}

STEP_SIZE=0.1/2.5
RVAL=-R0/180/5678/6378
#xyz2grd  ${DATAFILE} -G${DATAFILE}.grd -I${STEP_SIZE} -ZfLTw ${RVAL}
gmt xyz2grd -V  ${DATAFILE} -G${DATAFILE}.grd -I${STEP_SIZE} -ZLTwf ${RVAL}

JVAL=-Jpa0.002/90
gmt grdimage -V ${DATAFILE}.grd -C${CPTFILE} ${RVAL} ${JVAL}  -K -X2 -Yc > ${PSFILE}
gmt grdcontour  ${DATAFILE}.grd -C${CPTFILE} ${RVAL} ${JVAL}   -A- -O -K >> ${PSFILE}
gmt psbasemap  ${RVAL} ${JVAL}  -Ba10:Distance:/a200:Depth::.${DATAFILE0}:WESN -O -K >> ${PSFILE}

#  --- scale
gmt psscale -D12.75/-2/25/1.0h -C${CPTFILE} -B100:"Travel Time":/:sec: -X0 -Y0  -O >> ${PSFILE}
gmt psconvert ${PSFILE} -Tg -A -E450 -P