#!/bin/bash
mongo --eval "db.getSiblingDB('admin').shutdownServer()"
