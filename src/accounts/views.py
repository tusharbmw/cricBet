import json

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
from . import cricfeed
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny


# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def example_view(request, format=None):
    content = {
        'user': str(request.user),  # `django.contrib.auth.User` instance.
        'auth': str(request.auth),  # None
    }
    return Response(content)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def results_api_view(request):
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
                result = current_match.team1.name
            elif current_match.result == 'team2':
                result = current_match.team2.name
            else:
                result = 'Tied/No Result'
            matches_dict = {'team1': current_match.team1.name,
                            'team2': current_match.team2.name,
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
    if cnt >= 0:
        context['no_bets'] = cnt
    return Response(json.dumps(context, default=str))


@api_view(['POST'])
@permission_classes([AllowAny])
def register_api_view(request, format=None):
    data = request.data

    name = data['name']
    email = data['email']
    password1 = data['password']
    password2 = data['password2']

    if password1 == password2:
        if User.objects.filter(username=name).exists():
            return Response({'error': 'User already exists'})
        else:
            user = User.objects.create_user(username=name, password=password1, email=email)
            user.save()
            return Response({'success': 'User created successfully'})
    return Response({'error': 'Passwords do not match'})


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
        if td.days < 0:  # match has started, change status to IP
            next_match.result = "IP"
            next_match.save()
    upd_count = 0
    for current_match in Match.objects.filter(Q(result='IP')).order_by('datetime'):
        team1 = current_match.team1.name
        team2 = current_match.team2.name
        winner = cricfeed.get_match_info(current_match.match_id)
        if winner == "TBD" or winner == "IP":
            continue
        if winner == team1:
            update_match(current_match, 1)
            upd_count += 1
        elif winner == team2:
            update_match(current_match, 2)
            upd_count += 1
        elif winner == "No Winner":
            update_match(current_match, 0)
            upd_count += 1

    if upd_count > 0:
        return HttpResponse("%s matches updated" % str(upd_count))
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


def add_new_team(team_info):
    if Team.objects.filter(name=team_info['name']).exists():
        return
    t = Team(name=team_info['name'],
             logo_url=team_info['img'],
             description=team_info['shortname'],
             )
    t.save()
    return t


def add_new_match(match_info):
    if Team.objects.filter(name=match_info['Team1']).exists():
        team1 = Team.objects.filter(name=match_info['Team1'])[0]
    else:
        team1 = add_new_team(match_info['Team1Info'])
    # TODO: avoid so many db queries
    if Team.objects.filter(name=match_info['Team2']).exists():
        team2 = Team.objects.filter(name=match_info['Team2'])[0]
    else:
        team2 = add_new_team(match_info['Team2Info'])

    m = Match(match_id=match_info['match_id'],
              team1=team1,
              team2=team2,
              description=match_info['Description'],
              venue=match_info['venue'],
              result="TBD",
              datetime=datetime.strptime(match_info['datetime'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc),
              tournament=match_info['tournament']
              )
    m.save()


def fill_match(request):
    now = datetime.now(timezone.utc)
    matches_data = cricfeed.get_series_info()
    updated_cnt = 0
    for match_data in matches_data:
        print(match_data['datetime'])
        match_data_dt = datetime.strptime(match_data['datetime'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        if match_data_dt < now:
            print("Skipping as old match")
            continue
        elif Match.objects.filter(Q(match_id=match_data['match_id'])).exists():
            print("match already exist", match_data['match_id'])
            continue
        elif Match.objects.filter(Q(datetime=match_data_dt)).exists():
            print("match already exist at same time", match_data_dt)
            continue
        else:
            print("Lets add this match", match_data)
            add_new_match(match_data)
            updated_cnt += 1

    return HttpResponse("Total matches updated " + str(updated_cnt))


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


def whatsnew_view(request):
    whatsnew = [{'change': 'May 19,2024 Logic for match weight, API, design changes',
                 'description': 'Match points can now be different, initial support for APIs and UX changes'},
                {'change': 'April 17,2024 Logic for max skipped bet',
                 'description': 'if used too many skipped bets, user will get disqualified'},
                {'change': 'April 14,2024 Matches results', 'description': 'cric API integration for faster/accurate '
                                                                           'result updates'},
                {'change': 'April 13,2024 Matches auto add', 'description': 'cric API integration to pull match info'},
                {'change': 'April 12,2024 FA icons updated',
                 'description': 'Update FA icon version to v6.5.2 from v5.6.1'},
                {'change': 'April 12,2024 Package upgrades', 'description': 'Update Django and other python packages'},
                {'change': 'April 12,2024 Python upgrades', 'description': 'Upgrade to Python 3.10'},
                {'change': 'April 12,2024 Server update', 'description': 'Move from Cent OS 7 to Oracle Linux 9'},
                {'change': 'April 12,2024 DB upgrades', 'description': 'Update Database from sqllite to Oracle DB v19c'}
                ]
    return render(request, 'accounts/whatsnew.html', {'whatsnew': whatsnew})


def leaderboard(request):
    max_skipped_allowed = 30
    context = {}
    # initialize win and loss
    won = {}
    lost = {}
    skipped = {}
    matches_won = {}
    matches_lost = {}
    matches_with_result = Match.objects.filter(Q(result='team1') | Q(result='team2'))
    for u in User.objects.all():
        won[u.username] = 0
        lost[u.username] = 0
        skipped[u.username] = 0
        matches_won[u.username] = 0
        matches_lost[u.username] = 0
        for mr in matches_with_result:
            if mr.selection_set.filter(user=u).count() == 0:
                skipped[u.username] += 1

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
                won[u] += len(mr_sel2) * mr.match_points
                matches_won[u] += 1
            for u in mr_sel2:
                lost[u] += len(mr_sel1) * mr.match_points
                matches_lost[u] += 1
        else:  # team2 won
            for u in mr_sel1:
                lost[u] += len(mr_sel2) * mr.match_points
                matches_lost[u] += 1
            for u in mr_sel2:
                won[u] += len(mr_sel1) * mr.match_points
                matches_won[u] += 1
    total = {}

    for u in won.keys():
        total[u] = won[u] - lost[u]
    for u in skipped.keys():
        if skipped[u] > max_skipped_allowed:
            total[u] = -999
    context['total'] = sorted(total.items(), key=lambda x: x[1], reverse=True)
    context['lost'] = lost
    context['won'] = won
    context['skipped'] = skipped
    context['matches_won'] = matches_won
    context['matches_lost'] = matches_lost
    cnt = get_missing_bet_count(request.user)
    if cnt >= 0:
        context['no_bets'] = cnt
    return render(request, 'accounts/leaderboard.html', context)


@login_required(login_url='/login')
def dashboard(request):
    user = User.objects.get(username=request.user)
    #    selections = user.selection_set.all()
    last_match = Match.objects.filter(Q(result='team1') | Q(result='team2') | Q(result='NR')).order_by(
        'datetime').last()
    current_matches_obj = Match.objects.filter(Q(result='IP') | Q(result='DLD') | Q(result='TOSS')).order_by('datetime')
    next_match = Match.objects.filter(Q(result='TBD')).order_by('datetime').first()
    context = {}
    current_matches = []
    next_match_sel1 = []
    next_match_sel2 = []
    last_match_sel1 = []
    last_match_sel2 = []
    for current_match in current_matches_obj:
        current_match_sel1 = []
        current_match_sel2 = []
        # context['current_match'] = current_match
        for i in current_match.selection_set.all():
            if i.selection == current_match.team1:
                current_match_sel1.append(i.user.username)
            if i.selection == current_match.team2:
                current_match_sel2.append(i.user.username)
        matches_dict = {'team1': current_match.team1,
                        'team2': current_match.team2,
                        'id': current_match.id,
                        'datetime': current_match.datetime,
                        'result': current_match.result,
                        'venue': current_match.venue,
                        'description': current_match.description,
                        'match_sel1': ", ".join(current_match_sel1),
                        'match_sel2': ", ".join(current_match_sel2)}

        current_matches.append(matches_dict)
    context['current_matches'] = current_matches
    if next_match is not None:
        context['next_match'] = next_match
        for i in next_match.selection_set.all():
            if i.selection == next_match.team1 and i.hidden is False:
                next_match_sel1.append(i.user.username)
            if i.selection == next_match.team2 and i.hidden is False:
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
            # hidden bet logic
            if user != request.user and m.selection_set.filter(user=user).first().hidden:
                tmp_dict['none_checked'] = 'checked'
                tmp_dict['team1_checked'] = ''
                tmp_dict['team2_checked'] = ''

        matches_list.append(tmp_dict)
    cnt = get_missing_bet_count(request.user)
    if cnt >= 0:
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
    if cnt >= 0:
        context['no_bets'] = cnt
    return render(request, 'accounts/results.html', context)
