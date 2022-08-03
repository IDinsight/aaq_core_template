CREATE user :u1 with encrypted password :'p1';
GRANT :u1 TO admin_user;
CREATE user :u2 with encrypted password :'p2';
GRANT :u2 TO admin_user;

CREATE DATABASE development WITH OWNER :u1;
CREATE DATABASE test WITH OWNER :u2;