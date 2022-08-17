CREATE user :u1 with encrypted password :'p1';
GRANT :u1 TO admin_user;
CREATE user :u2 with encrypted password :'p2';
GRANT :u2 TO admin_user;

CREATE DATABASE :d1 WITH OWNER :u1;
CREATE DATABASE :d2 WITH OWNER :u2;