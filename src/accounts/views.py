from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from teams.models import *
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from datetime import timezone, datetime, timedelta
from django.template.defaulttags import register
import urllib.request as urllib2
from xml.etree.ElementTree import fromstring
import re

hdr = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive'}


# Create your views here.
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


def get_missing_bet_count(user):
    try:
        user = User.objects.get(username=user)
    except:
        return -1
    if user is None:
        return -1
    cnt = 0
    now = datetime.now(timezone.utc)
    matches = Match.objects.filter(datetime__gte=now, datetime__lte=now + timedelta(days=5)).order_by('datetime')
    for m in matches:
        if m.selection_set.filter(user=user).count() == 0:
            cnt += 1
    return cnt


def home(request):
    return HttpResponse("Hello , welcome to TushCricBet")


def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('schedule')
        else:
            messages.info(request, 'Username or Password incorrect')
    context = {}
    return render(request, 'accounts/login.html', context)


@login_required(login_url='/login')
def logout_page(request):
    logout(request)
    messages.info(request, 'User Successfully logged out')
    return redirect('login')


@login_required(login_url='/login')
def update(request):
    if request.method == "POST":
        user = User.objects.get(username=request.user)
        now = datetime.now(timezone.utc)
        err = 0
        for key, value in request.POST.items():
            if key.startswith("options_"):
                match_id = key.split('_')[1]
                match = Match.objects.get(id=match_id)
                match_date = match.datetime
                td = match_date - now
                if td.days < 0:
                    # match has already started
                    continue

                if value in ('team1', 'team2'):
                    if value == 'team1':
                        team = match.team1
                    else:
                        team = match.team2
                    try:
                        obj = Selection.objects.get(user=user, match=match)
                        obj.selection = team
                        obj.save()
                    except Selection.DoesNotExist:
                        Selection.objects.create(selection=team, user=user, match=match)
                    except:
                        err += 1

                else:
                    team = None
                    # delete row
                    try:
                        obj = Selection.objects.get(user=user, match=match)
                        obj.delete()
                    except Selection.DoesNotExist:
                        pass  # Nothing to delete
                    except:
                        err += 1
    if err == 0:
        messages.success(request, "Picks saved successfully. Good Luck! ")
    else:
        messages.error(request, "Issue in saving picks. Please try again later")
    return redirect('schedule')


def maintain(request):
    now = datetime.now(timezone.utc)
    next_match = Match.objects.filter(result='TBD').order_by('datetime').first()
    if next_match is not None:
        td = next_match.datetime - now
        if td.days < 0: #match has started, change status to IP
            next_match.result = "IP"
            next_match.save()
    current_match = Match.objects.filter(Q(result='IP')).order_by('datetime').first()
    if current_match is not None:
        now4 = now - timedelta(hours=4)
        td4 = current_match.datetime - now4
        team1 = current_match.team1.name
        team2 = current_match.team2.name
        req = urllib2.Request("http://static.cricinfo.com/rss/livescores.xml", None, hdr)
        html_page = urllib2.urlopen(req)
        xml_page = html_page.read()
        tree = fromstring(xml_page)
        live = ""
        for child in tree.iter('item'):
            if (team1 in child[0].text) and (team2 in child[0].text):
                # print(child[0].text) # TODO to remove
                live = child[0].text
        stats = [[0, 0], [0, 0]]  # team1, team2 [runs, wickets , batting]
        # print("teams are ", team1, team2)
        # print("input is : ", live)  # TODO remove
        batting = None
        for s in live.split('v'):
            if team1 in s:
                tm = 0
            else:
                tm = 1
            if '*' in s:
                batting = tm

            i = 0
            for j in re.findall(r'\d+', s):
                i += 1
                if i == 1:
                    stats[tm][0] = int(j)
                if i == 2:
                    stats[tm][1] = int(j)

        # print(stats, batting, td4.days)  # TODO remove

        if (batting is not None) and (td4.days >= 0):  # someone is batting
            # check batting team scored more and is batting second
            if stats[1-batting][0] > 0 and stats[batting][0] > stats[1 - batting][0]:
                # print("team", batting + 1, "has won")   # TODO remove this
                update_match(current_match, batting+1)

            if stats[batting][1] == 10 and stats[batting][0] < stats[1 - batting][0]:  # team batting second lost
                # print("team", batting + 1, "has lost")  # TODO remove this
                update_match(current_match, 1 - batting + 1)
        else:  # match has not started or ended
            if stats[0][0] > 0 and stats[1][0] > 0:  # Match completed
                if stats[0][0] > stats[1][0]:
                    # print("Team1 has won")  # TODO remove this
                    update_match(current_match, 1)
                elif stats[0][0] == stats[1][0]:
                    # print("Match is Tied")  # TODO remove this
                    update_match(current_match, 0)
                else:
                    # print("Team2 has won")  # TODO remove this
                    update_match(current_match, 2)
        return HttpResponse(" " + str(stats) + "batting :" + str(batting) + " td4 days:" + str(td4.days))
    return HttpResponse("No Match to update")


def update_match(obj, team):
    # print("update match has been called for team = ", team) # TODO remove this
    if team == 1:
        obj.result = 'team1'
    elif team == 2:
        obj.result = 'team2'
    else:
        obj.result = 'NR'
    obj.save()


def register_page(request):
    form = UserCreationForm()
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.cleaned_data.get('username')
            messages.success(request, 'Account Created Successfully for User: ' + user + ' . Please login.')
            return redirect('login')

    context = {'form': form}
    return render(request, 'accounts/register.html', context)


def contact(request):
    return HttpResponse("Ping me on my whatsapp ")


def teams_view(request):
    teams = Team.objects.all()

    return render(request, 'accounts/teams.html', {'teams': teams})


def leaderboard(request):
    context = {}
    # initialize win and loss
    won = {}
    lost = {}
    for u in User.objects.all():
        won[u.username] = 0
        lost[u.username] = 0
    matches_with_result = Match.objects.filter(Q(result='team1') | Q(result='team2'))
    for mr in matches_with_result:
        mr_sel1 = []
        mr_sel2 = []
        for s in mr.selection_set.all():
            if s.selection == mr.team1:
                mr_sel1.append(s.user.username)
            if s.selection == mr.team2:
                mr_sel2.append(s.user.username)
        if mr.result == "team1":
            for u in mr_sel1:
                won[u] += len(mr_sel2)
            for u in mr_sel2:
                lost[u] += len(mr_sel1)
        else:   # team2 won
            for u in mr_sel1:
                lost[u] += len(mr_sel2)
            for u in mr_sel2:
                won[u] += len(mr_sel1)
    total = {}

    for u in won.keys():
        total[u] = won[u]-lost[u]
    context['total'] = sorted(total.items(), key=lambda x: x[1], reverse=True)
    context['lost'] = lost
    context['won'] = won
    cnt = get_missing_bet_count(request.user)
    if cnt >= 0:
        context['no_bets'] = cnt
    return render(request, 'accounts/leaderboard.html', context)


@login_required(login_url='/login')
def dashboard(request):
    user = User.objects.get(username=request.user)
#    selections = user.selection_set.all()
    last_match = Match.objects.filter(Q(result='team1') | Q(result='team2') | Q(result='NR')).order_by('datetime').last()
    current_match = Match.objects.filter(Q(result='IP')).order_by('datetime').first()
    next_match = Match.objects.filter(Q(result='TBD')).order_by('datetime').first()
    context = {}
    current_match_sel1 = []
    current_match_sel2 = []
    next_match_sel1 = []
    next_match_sel2 = []
    last_match_sel1 = []
    last_match_sel2 = []

    if current_match is not None:
        context['current_match'] = current_match
        for i in current_match.selection_set.all():
            if i.selection == current_match.team1:
                current_match_sel1.append(i.user.username)
            if i.selection == current_match.team2:
                current_match_sel2.append(i.user.username)
        context['current_match_sel1'] = ", ".join(current_match_sel1)
        context['current_match_sel2'] = ", ".join(current_match_sel2)

    if next_match is not None:
        context['next_match'] = next_match
        for i in next_match.selection_set.all():
            if i.selection == next_match.team1:
                next_match_sel1.append(i.user.username)
            if i.selection == next_match.team2:
                next_match_sel2.append(i.user.username)
        context['next_match_sel1'] = ", ".join(next_match_sel1)
        context['next_match_sel2'] = ", ".join(next_match_sel2)
        context['next_match_timer'] = int(next_match.datetime.timestamp() * 1000)

    if last_match is not None:
        context['last_match'] = last_match
        for i in last_match.selection_set.all():
            if i.selection == last_match.team1:
                last_match_sel1.append(i.user.username)
            if i.selection == last_match.team2:
                last_match_sel2.append(i.user.username)
        context['last_match_sel1'] = ", ".join(last_match_sel1)
        context['last_match_sel2'] = ", ".join(last_match_sel2)

    cnt = get_missing_bet_count(request.user)
    if cnt >= 0:
        context['no_bets'] = cnt

    return render(request, 'accounts/dashboard.html', context)


@login_required(login_url='/login')
def schedule_view(request, pk=''):
    try:
        user = User.objects.get(username=pk)
    except User.DoesNotExist:
        user = User.objects.get(username=request.user)

    #    user = User.objects.get(username="test1")
    if user == request.user:
        disabled = ''
    else:
        disabled = 'disabled'
    context = {}
    matches_list = []
    now = datetime.now(timezone.utc)
    matches = Match.objects.filter(datetime__gte=now, datetime__lte=now + timedelta(days=5)).order_by('datetime')
    for m in matches:
        tmp_dict = {'none_checked': '',
                    'team1_checked': '',
                    'team2_checked': '',
                    'team1': m.team1,
                    'team2': m.team2,
                    'id': m.id,
                    'datetime': m.datetime,
                    'result': m.result,
                    'venue': m.venue,
                    'description': m.description}
        if m.selection_set.filter(user=user).count() == 0:
            tmp_dict['none_checked'] = 'checked'
        else:
            if m.selection_set.filter(user=user).first().selection == m.team1:
                tmp_dict['team1_checked'] = 'checked'
            else:
                tmp_dict['team2_checked'] = 'checked'
        matches_list.append(tmp_dict)
    cnt = get_missing_bet_count(request.user)
    if cnt >=0:
        context['no_bets'] = cnt
    context['matches_list'] = matches_list
    context['uname'] = user.username
    context['disabled'] = disabled
    return render(request, 'accounts/schedule.html', context)

@login_required(login_url='/login')
def results_view(request):

    matches_obj = Match.objects.filter(Q(result='team1') | Q(result='team2') | Q(result='NR')).order_by('datetime')
    context = {}
    matches = []
    for current_match in matches_obj:
        current_match_sel1 = []
        current_match_sel2 = []
        result = ''
        if current_match is not None:
            for i in current_match.selection_set.all():
                if i.selection == current_match.team1:
                    current_match_sel1.append(i.user.username)
                if i.selection == current_match.team2:
                    current_match_sel2.append(i.user.username)

            if current_match.result == 'team1':
                result = current_match.team1
            elif current_match.result == 'team2':
                result = current_match.team2
            else:
                result = 'Tied/No Result'
            matches_dict = {'team1': current_match.team1,
                    'team2': current_match.team2,
                    'id': current_match.id,
                    'datetime': current_match.datetime,
                    'result': result,
                    'venue': current_match.venue,
                    'description': current_match.description,
                    'match_sel1': ", ".join(current_match_sel1),
                    'match_sel2': ", ".join(current_match_sel2)}

            matches.append(matches_dict)

    context["matches"] = matches
    cnt = get_missing_bet_count(request.user)
    if cnt >=0:
        context['no_bets'] = cnt
    return render(request, 'accounts/results.html', context)

