#!/usr/bin/python2

import re

class BaseValue(object):
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return value

	def __repr__(self):
		return "<%s object: %s>" % (self.__class__.__name__, self.__str__())

	def to_value(self):
		return self.__str__()

# Note:
# to_value: generates value as expected by set_claim (py obj)
# from_value: expects datavalue.value as provided by get_claims (py obj)

class Property(BaseValue):
	def __init__(self, id):
		if isinstance(id, str):
			self.id = int(id.upper().replace("P", ""))
		else:
			self.id = id

	def __str__(self):
		return "P%i" % self.id

	def to_value(self):
		return {"entity-type": "property", "numeric-id": self.id}

	@classmethod
	def from_value(cls, value):
		assert value["entity-type"] == "property"
		return cls(value["numeric-id"])

class Item(BaseValue):
	def __init__(self, id):
		if isinstance(id, str):
			self.id = int(id.upper().replace("Q", ""))
		else:
			self.id = id

	def __str__(self):
		return "Q%i" % self.id

	def to_value(self):
		return {"entity-type": "item", "numeric-id": self.id}

	@classmethod
	def from_value(cls, value):
		# ok this is ugly...
		if value["entity-type"] == "property":
			return Property.from_value(value)
		assert value["entity-type"] == "item"
		return cls(value["numeric-id"])

class String(BaseValue):
	def __str__(self):
		return self.value

	def to_value(self):
		return self.value

	@classmethod
	def from_value(cls, value):
		return cls(value)

class Time(BaseValue):
	# wikibase uses a datetime format based on ISO8601
	# eg: +00000002013-01-01T00:00:00Z
	iso8601_re = re.compile(r"(?P<ysign>[\+\-])(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)T(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)Z")

	def __init__(self, time, timezone=0, before=0, after=0, precision=11, calendarmodel="http://www.wikidata.org/entity/Q1985727"):
		self.time = time
		self.timezone = timezone
		self.before = before
		self.after = after
		self.precision = precision # FIXME: allow string input
		self.calendarmodel = calendarmodel

	def __str__(self):
		return self.to_value()["time"]

	def to_value(self):
		ysign = '+' if self.time["year"] >= 0 else '-'
		value_out = {
			"time": ysign + "%(year)011i-%(month)02i-%(day)02iT%(hour)02i:%(minute)02i:%(second)02iZ" % self.time,
			"timezone": self.timezone,
			"before": self.before,
			"after": self.after,
			"precision": self.precision,
			"calendarmodel": self.calendarmodel,
		}
		return value_out

	@classmethod
	def from_value(cls, value):
		#FIXME: catch error exception when match is empty - raise proper error
		time_raw = Time.iso8601_re.match(value["time"]).groupdict()
		value_in = {
			"time": {
				"year": int("%(ysign)s%(year)s" % time_raw),
				"month": int(time_raw["month"]),
				"day": int(time_raw["day"]),
				"hour": int(time_raw["hour"]),
				"minute": int(time_raw["minute"]),
				"second": int(time_raw["second"]),
			},
			"timezone": value["timezone"],
			"before": value["before"],
			"after": value["after"],
			"precision": value["precision"],
			"calendarmodel": value["calendarmodel"],
		}
		return cls(**value_in)

class GlobeCoordinate(BaseValue):
	def __init__(self, latitude, longitude, precision=0.000001, globe="http://www.wikidata.org/entity/Q2"):
		self.latitude = latitude
		self.longitude = longitude
		self.precision = precision # in degrees (or fractions of)
		self.globe = globe

	def __str__(self):
		return "%f, %f" % (self.latitude, self.longitude)

	def to_value(self):
		value_out = {
			"latitude": self.latitude,
			"longitude": self.longitude,
			"precision": self.precision,
			"globe": self.globe,
		}
		return value_out

	@classmethod
	def from_value(cls, value):
		try:
			del value['altitude']
		except KeyError:
			pass
		return cls(**value)

# datavalue.type -> type class
types = {
	"wikibase-entityid": Item, # or Property
	"string": String,
	"time": Time,
	"globecoordinate": GlobeCoordinate,
}

def thing_from_datavalue(datavalue):
	return types[datavalue["type"]].from_value(datavalue["value"])
