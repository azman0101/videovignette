#!/bin/bash

kill `ps axu | grep pydevd | awk '{print $2}'`
