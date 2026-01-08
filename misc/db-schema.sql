CREATE EXTENSION tablefunc;

CREATE TABLE document(
  id SERIAL PRIMARY KEY,
  data JSON NOT NULL,
  checksum VARCHAR(128) NOT NULL UNIQUE,
  created_utc BIGINT NOT NULL DEFAULT extract(epoch from now())::int,
  updated_utc BIGINT NOT NULL DEFAULT extract(epoch from now())::int
);


CREATE SEQUENCE question_id START 8888 NO CYCLE;
CREATE TABLE question(
    id int NOT NULL PRIMARY KEY default nextval('question_id'),
    did integer,		-- document id
    data json NOT NULL,
    preset_answer JSON,
    checksum VARCHAR(128) NOT NULL,
    tags INT[] NOT NULL default '{}',
    status INTEGER NOT NULL default 1, -- 1_todo, 2_finish, 3_verify, 4_disaccord, 5_accordance
    health INTEGER NOT NULL default 1,
    created_utc BIGINT NOT NULL default extract(epoch from now())::int,
    updated_utc BIGINT NOT NULL default extract(epoch from now())::int
);
CREATE UNIQUE INDEX uix_question ON question(checksum);
CREATE INDEX ix_question_did ON question (did);

CREATE SEQUENCE answer_id START 8888 NO CYCLE;
CREATE TABLE answer(
    id int NOT NULL  PRIMARY KEY default nextval('answer_id'),
    data json NOT NULL,
    qid int NOT NULL,		-- question id
    uid int NOT NULL,		-- user id
    status INTEGER NOT NULL default 1, -- 0_invalid, 1_valid, 2_unfinished
    standard int NOT NULL default 0,   -- ?
    result int NOT NULL default 0,  -- 0_waiting(not reached judge threshold) 1_correct 2_wrong 3_nonconclusion(conflict but not judged)
    created_utc BIGINT NOT NULL default extract(epoch from now())::int,
    updated_utc BIGINT NOT NULL default extract(epoch from now())::int
);
CREATE UNIQUE INDEX uix_answer ON answer(qid, uid);

CREATE SEQUENCE tag_id START 1 NO CYCLE;
CREATE TABLE tag(
    id int NOT NULL  PRIMARY KEY default nextval('tag_id'),
    name VARCHAR(64) NOT NULL,
    status INTEGER NOT NULL default 1,
    created_utc BIGINT NOT NULL default extract(epoch from now())::int,
    updated_utc BIGINT NOT NULL default extract(epoch from now())::int
);
CREATE UNIQUE INDEX uix_tag ON tag(name);

CREATE TABLE mold (		-- scheme
  id SERIAL PRIMARY KEY,
  checksum VARCHAR(128) NOT NULL,
  name VARCHAR(128) NOT NULL UNIQUE,
  data JSON,
  created_utc INT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::INT,
  updated_utc INT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::INT
);

-- alter table question add column health INTEGER NOT NULL default 1;
-- update question set health = 0 where status = 2;

-- alter table answer add column standard int NOT NULL default 0;
-- alter table answer add column result int NOT NULL default 0;
-- update answer set status = 1 where status = 0;
-- update answer set standard = 1 where uid = 9009;


-- 2017-11-29 pdf 表格标注

-- ALTER TABLE question ADD COLUMN did INTEGER;
-- ALTER TABLE question ADD COLUMN preset_answer JSON;
-- CREATE INDEX ix_question_did ON question (did);

-- CREATE TABLE document(
--   id SERIAL PRIMARY KEY,
--   data JSON NOT NULL,
--   checksum VARCHAR(128) NOT NULL UNIQUE,
--   created_utc BIGINT NOT NULL DEFAULT extract(epoch from now())::int,
--   updated_utc BIGINT NOT NULL DEFAULT extract(epoch from now())::int
-- );

-- 2017-12-16

-- CREATE TABLE mold (
--   id SERIAL PRIMARY KEY,
--   checksum VARCHAR(128) NOT NULL UNIQUE,
--   name VARCHAR(128) NOT NULL,
--   data JSON NOT NULL,
--   created_utc INT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::INT,
--   updated_utc INT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::INT
-- );

-- 2017-12-19

-- ALTER TABLE IF EXISTS mold DROP CONSTRAINT IF EXISTS mold_checksum_key;
-- ALTER TABLE IF EXISTS mold ADD CONSTRAINT mold_name_key UNIQUE(name);
-- ALTER TABLE IF EXISTS mold ALTER COLUMN data DROP NOT NULL;

-- 2018-01-15
-- ****** IMPORTANT *******
-- DO NOT USE THIS FILE TO RECORD DB CHANGE ANY MORE
-- USE ALEMBIC INSTEAD
