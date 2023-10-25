#!/bin/bash
while [ 1 ]
do
    aplay -D plughw:$1,$2 $3
done
