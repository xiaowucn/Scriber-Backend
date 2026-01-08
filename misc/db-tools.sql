-- Update updated_utc when not set
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
    --  WHEN (NEW.* IS DISTINCT FROM OLD.*)  -- could not identify an equality operator for type json
    EXECUTE PROCEDURE auto_updated_utc();
