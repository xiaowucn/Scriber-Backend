import json
import logging
import re
from copy import deepcopy

from asyncpg import UniqueViolationError
from sqlalchemy import Column, inspect, true
from sqlalchemy.sql import Join
from sqlalchemy.sql.elements import UnaryExpression

from remarkable.common.constants import TagType
from remarkable.common.util import generate_timestamp
from remarkable.db import db
