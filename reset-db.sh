#!/bin/bash

if [ -f /tmp/rm_query.sql ]
then
    echo "Removing old rm_query"
    rm /tmp/rm_query.sql
fi

echo "Enter your user password and then your mysql password"
su - dev -c "mysql -u dev -p -e \"SELECT concat('DROP TABLE IF EXISTS ', table_name, ';') FROM information_schema.tables WHERE table_schema = 'videodb' INTO OUTFILE '/tmp/rm_query.sql';\""
su - dev -c "sed -i '1s/^/SET FOREIGN_KEY_CHECKS=0;/' /tmp/rm_query.sql"
su - dev -c "echo 'SET FOREIGN_KEY_CHECKS=1;' >> /tmp/rm_query.sql"
echo 'Table removing : \n'
cat /tmp/rm_query.sql
echo '\n'
mysql -u dev -p videodb < /tmp/rm_query.sql
#rm /tmp/rm_query.sql