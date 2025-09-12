exit
dir
mv core valencafm/
dir
mv db.sqlite3 valencafm/
mv financas_radio valencafm/
mv manage.py valencafm/
dir
mv media valencafm/
mv static valencafm/
dir
mv virtual valencafm/
dir
cd valencafm
dir
exit
dir
unzip valencafm.zip
dir
cd valencafm
dir
pip install -r requirements.txt
workon virtual
mkvirtualenv virtual
workon virtual
pip install -r requirements.txt
python manage.py runserver 
~venv
dir
exit
