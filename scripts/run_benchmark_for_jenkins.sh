#!/bin/bash
# run_benchmark_for_jenkins.sh ---
#
# Filename: run_benchmark_for_jenkins.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Dec  2 18:24:48 2013 (+0100)

# Commentary:
# %*% This script runs the tests passed as argument using nose with all the
# %*% flags needed to generate all the data to generate the reports used in
# %*% the jenkins experiments.
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:


set -e

# @CONF_OPTION NOSE_RUN_DIR: Specify from which directory nose should run (default is $PWD)
if [ ! -z "$NOSE_RUN_DIR" ]; then
    cd $NOSE_RUN_DIR
fi

echo Nose will run from $PWD

# TODO(emilon): Make the timeout configurable

# @CONF_OPTION NOSE_TESTS_TO_RUN: Specify which tests to run in nose syntax. (default is everything nose can find from within NOSE_RUN_DIR)
NOSECMD="nosetests -v --all-modules --traverse-namespace --cover-package=Tribler --cover-inclusive $NOSE_TESTS_TO_RUN --logging-format='%(levelname)-7s %(created).2f %(module)15s:%(lineno)-4d  %(message)s'"
process_guard.py -t 3600 -m $OUTPUT_DIR -c "$NOSECMD"

echo Nose finished.

#
# run_benchmark_for_jenkins.sh ends here
