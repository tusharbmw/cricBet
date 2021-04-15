# CricBet
Using Django to make a app to be used/tested with friends

#setup steps:
update db info in cricBet settings.py

to update changes use

python manage.py makemigrations

python manage.py migrate -- to create db

To run on server:
python manage.py runserver 0.0.0.0:5000 &



open firewall: 

sudo iptables --list --line-numbers

iptables -P INPUT ACCEPT

iptables -P OUTPUT ACCEPT

iptables -P FORWARD ACCEPT

iptables -F
