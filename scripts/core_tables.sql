DROP TABLE IF EXISTS faqmatches;

CREATE TABLE faqmatches (
	faq_id serial NOT NULL,
	faq_added_utc timestamp without time zone NOT NULL,
	faq_author text NOT NULL,
	faq_title text NOT NULL,
	faq_content_to_send text NOT NULL,
	faq_tags text [] NOT NULL,
	faq_thresholds real [] NOT NULL,
	PRIMARY KEY (faq_id)
);

DROP TABLE IF EXISTS inbounds;

CREATE TABLE inbounds (
	inbound_id serial NOT NULL,
	feedback_secret_key text NOT NULL,
	inbound_text text NOT NULL,
	inbound_metadata json,
	inbound_utc timestamp without time zone NOT NULL,
	model_scoring json NOT NULL,
	returned_content json NOT NULL,
	returned_utc timestamp without time zone NOT NULL,
	returned_feedback json,
	PRIMARY KEY (inbound_id)
);
