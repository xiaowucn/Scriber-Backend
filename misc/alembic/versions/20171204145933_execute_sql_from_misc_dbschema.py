"""execute sql from misc dbschema

Revision ID: 38db66e3a598
Revises:
Create Date: 2017-12-04 14:59:33.849923

"""

from alembic import op

from remarkable.config import get_config

# revision identifiers, used by Alembic.
revision = "38db66e3a598"
down_revision = None
branch_labels = None
depends_on = None


def run_postgresql():
    op.execute(
        r"""
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
    did integer,
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
    qid int NOT NULL,
    uid int NOT NULL,
    status INTEGER NOT NULL default 1, -- 0_invalid, 1_valid, 2_unfinished
    standard int NOT NULL default 0,
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

CREATE TABLE mold (
  id SERIAL PRIMARY KEY,
  checksum VARCHAR(128) NOT NULL,
  name VARCHAR(128) NOT NULL UNIQUE,
  data JSON,
  created_utc INT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::INT,
  updated_utc INT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::INT
);

CREATE OR REPLACE FUNCTION auto_updated_utc() RETURNS TRIGGER AS $BODY$
BEGIN
    IF NOT EXISTS(SELECT regexp_matches(current_query(), '\s+updated_utc\s*=', 'i')) THEN
        NEW.updated_utc := EXTRACT(EPOCH FROM now())::INT;
    END IF;
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS auto_mold_updated_utc ON mold;
CREATE TRIGGER auto_mold_updated_utc
    BEFORE UPDATE
    ON mold
    FOR EACH ROW
    EXECUTE PROCEDURE auto_updated_utc();
    """
    )


def run_mysql():
    op.execute("""
    -- 创建 document 表
CREATE TABLE document (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data JSON NOT NULL,
    checksum VARCHAR(128) NOT NULL ,
    created_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    updated_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    unique index document_checksum_key (checksum)
);
""")

    op.execute("""
-- 创建 question 表
CREATE TABLE question (
    id INT AUTO_INCREMENT PRIMARY KEY,
    did INT,
    data JSON NOT NULL,
    preset_answer JSON,
    checksum VARCHAR(128) NOT NULL,
    tags JSON NOT NULL,
    status INT NOT NULL DEFAULT 1, -- 1_todo, 2_finish, 3_verify, 4_disaccord, 5_accordance
    health INT NOT NULL DEFAULT 1,
    created_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    updated_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    UNIQUE INDEX uix_question (checksum)
);""")

    op.execute("""
-- 创建 answer 表
CREATE TABLE answer (
    id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    data JSON NOT NULL,
    qid INT NOT NULL,
    uid INT NOT NULL,
    status INT NOT NULL DEFAULT 1, -- 0_invalid, 1_valid, 2_unfinished
    standard INT NOT NULL DEFAULT 0,
    result INT NOT NULL DEFAULT 0,  -- 0_waiting(not reached judge threshold) 1_correct 2_wrong 3_nonconclusion(conflict but not judged)
    created_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    updated_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    UNIQUE INDEX uix_answer (qid, uid)
) ;
""")

    op.execute("""
-- 创建 tag 表
CREATE TABLE tag (
    id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(64) NOT NULL,
    status INT NOT NULL DEFAULT 1,
    created_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    updated_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    UNIQUE INDEX uix_tag (name)
);
""")

    op.execute("""
-- 创建 mold 表
CREATE TABLE mold (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checksum VARCHAR(128) NOT NULL,
    name VARCHAR(128) NOT NULL,
    data JSON,
    created_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    updated_utc int NOT NULL DEFAULT (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())),
    unique index mold_name_key (name)
);
    """)


def upgrade():
    if get_config("db.type") == "mysql":
        run_mysql()
    else:
        run_postgresql()


def downgrade():
    pass
