from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from teams.models import *
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from datetime import timezone, datetime, timedelta
from .forms import CreateUserFroms

# Create your views here.


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
            messages.info(request,'Username or Password incorrect')
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
        for key, value in request.POST.items():
            if key.startswith("options_"):
                match_id = key.split('_')[1]
                print('Match ID: %s' % (match_id))
                match = Match.objects.get(id=match_id)
                match_date=match.datetime
                td = match_date - now
                if td.days < 0:
                    #match has already started
                    continue

                if value in ('team1', 'team2'):
                    if value == 'team1':
                        team = match.team1
                    else:
                        team= match.team2
                    try:
                        obj=Selection.objects.get(user=user, match=match)
                        obj.selection=team
                        obj.save()
                    except Selection.DoesNotExist:
                        Selection.objects.create(selection=team, user=user, match=match)

                else:
                    team = None
                    #delete row
                    try:
                        obj=Selection.objects.get(user=user, match=match)
                        obj.delete()
                    except Selection.DoesNotExist:
                        pass #Nothing to delete
                print('Value %s' % (value))
                print('Team %s' % (team))

    return redirect('schedule')



def register_page(request):
    form = UserCreationForm()
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.cleaned_data.get('username')
            messages.success(request, 'Account Created Successfully for User: '+user+' . Please login.')
            return redirect('login')

    context = {'form': form}
    return render(request, 'accounts/register.html', context)


def contact(request):
    return HttpResponse("Ping me on my whatsapp ")


def teams_view(request):
    teams = Team.objects.all()

    return render(request, 'accounts/teams.html', {'teams': teams})


@login_required(login_url='/login')
def dashboard(request):
    user = User.objects.get(username=request.user)
    selections = user.selection_set.all()
    return render(request, 'accounts/dashboard.html', {'selections': selections})


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

    matches_list = []
    now = datetime.now(timezone.utc)
    matches = Match.objects.filter(datetime__gte=now, datetime__lte=now+timedelta(days=5))
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
    return render(request, 'accounts/schedule.html',
                  {'matches_list': matches_list, 'uname': user.username, 'disabled': disabled})
