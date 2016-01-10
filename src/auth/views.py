# import  os
from flask import (Blueprint, escape, flash, render_template,
                   redirect, request, url_for, jsonify, abort)
from flask_login import current_user, login_required, login_user, logout_user
# from werkzeug.utils import secure_filename
from sqlalchemy import func, asc, Date, cast, extract
from sqlalchemy.types import DateTime
from .forms import ResetPasswordForm, EmailForm, LoginForm, RegistrationForm, EditUserForm, username_is_available, \
    email_is_available, Editdate, GroupInsertForm, TimecardInsertForm, AddUserToGroupForm, \
    MonthInsert, FileUploadForm, GroupForm, AssignTimecardForm
from ..data.database import db
from ..data.models import User, UserPasswordToken, Card, User_has_group, Group, Group_has_timecard, Timecard
from ..data.util import generate_random_token
from ..decorators import reset_token_required
from ..emails import send_activation, send_password_reset
from ..extensions import login_manager
from datetime import datetime, timedelta
from .xmlparse import mujxmlparse
from django.utils.safestring import mark_safe
import simplejson


def last_day_of_month(year, month):
    """ Work out the last day of the month """
    last_days = [31, 30, 29, 28, 27]
    for i in last_days:
        try:
            end = datetime(year, month, i)
        except ValueError:
            continue
        else:
            return end.day
    return None


blueprint = Blueprint('auth', __name__)


@blueprint.route('/activate', methods=['GET'])
def activate():
    " Activation link for email verification "
    userid = request.args.get('userid')
    activate_token = request.args.get('activate_token')

    user = db.session.query(User).get(int(userid)) if userid else None
    if user and user.is_verified():
        flash("Your account is already verified.", 'info')
    elif user and user.activate_token == activate_token:
        user.update(verified=True)
        flash("Thank you for verifying your email. Your account is now activated", 'info')
        return redirect(url_for('public.index'))
    else:
        flash("Invalid userid/token combination", 'warning')

    return redirect(url_for('public.index'))


@blueprint.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = EmailForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data)
        if user:
            reset_value = UserPasswordToken.get_or_create_token(user.id).value
            send_password_reset(user, reset_value)
            flash("Passowrd reset instructions have been sent to {}. Please check your inbox".format(user.email),
                  'info')
            return redirect(url_for("public.index"))
        else:
            flash("We couldn't find an account with that email. Please try again", 'warning')
    return render_template("auth/forgot_password.tmpl", form=form, user=current_user)


@login_manager.user_loader
def load_user(userid):  # pylint: disable=W0612
    "Register callback for loading users from session"
    return db.session.query(User).get(int(userid))


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data)
        if user and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            flash("Logged in successfully", "info")
            return redirect(request.args.get('next') or url_for('public.index'))
        else:
            flash("Invalid email/password combination", "danger")
    return render_template("auth/login.tmpl", form=form, user=current_user)


@blueprint.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for('public.index'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User.create(**form.data)
        login_user(new_user)
        send_activation(new_user)
        flash("Thanks for signing up {}. Welcome!".format(escape(new_user.username)), 'info')
        return redirect(url_for('public.index'))
    return render_template("auth/register.tmpl", form=form, user=current_user)


@blueprint.route('/resend_activation_email', methods=['GET'])
@login_required
def resend_activation_email():
    if current_user.is_verified():
        flash("This account has already been activated.", 'warning')
    else:
        current_user.update(activate_token=generate_random_token())
        send_activation(current_user)
        flash('Activation email sent! Please check your inbox', 'info')

    return redirect(url_for('public.index'))


@blueprint.route('/reset_password', methods=['GET', 'POST'])
@reset_token_required
def reset_password(userid, user_token):
    user = db.session.query(User).get(userid)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.update(password=form.password.data)
        user_token.update(used=True)
        flash("Password updated! Please log in to your account", "info")
        return redirect(url_for('public.index'))
    return render_template("auth/reset_password.tmpl", form=form, user=current_user)


@blueprint.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    user = db.session.query(User).get(current_user.id)
    form = EditUserForm(obj=user)
    if current_user.access == "B" or current_user.access == 'U':
        form.access.choices = [('U', 'User')]
        card = form.card_number.data
    if form.validate_on_submit():
        if form.username.data <> current_user.username:
            if not username_is_available(form.username.data):
                flash("Username is not allowed use another", "warning")
                return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)
        if form.email.data <> current_user.email:
            if not email_is_available(form.email.data):
                flash("Email is used use another email", "warning")
                return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)
        if current_user.access <> "A":
            form.card_number.data = card
        new_user = user.update(**form.data)
        login_user(new_user)
        flash("Saved successfully", "info")
        return redirect(request.args.get('next') or url_for('public.index'))

    return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)


@blueprint.route('/vypisy_vyber', methods=['GET', 'POST'])
@login_required
def mesicni_vypis_vyber():
    form = MonthInsert()
    if form.validate_on_submit():
        return redirect('/sestava_vsichni/' + form.month.data)
    return render_template('auth/recreatemonth.tmpl', form=form, user=current_user)


@blueprint.route('/sestava_vsichni/<string:mesic>', methods=['GET'])
@login_required
def sestava_vsichni(mesic):
    form = db.session.query(User.card_number.label('card_number'), User.second_name.label('fullname'),
                            func.DATE_FORMAT(Card.time, '%Y-%m').label("time"), \
                            func.DATE_FORMAT(Card.time, '%Y').label("year"),
                            func.DATE_FORMAT(Card.time, '%m').label("month")). \
        join(Card, User.card_number == Card.card_number).group_by(func.DATE_FORMAT(Card.time, '%Y-%m'), User.second_name). \
        filter(func.DATE_FORMAT(Card.time, '%Y-%m') == mesic). \
        order_by(User.second_name).all()
    poledat = []
    for u in form:
        prom = pole_calendar(int(u[0]), int(u[3]), int(u[4]))
        poledat.append(prom)
    # print poledat
    if len(form) == 0:
        flash("No data", category="info")
        return redirect(url_for("auth.mesicni_vypis_vyber"))
    else:
        return render_template("auth/sestava_vsichni.tmpl", data=poledat, form=form, user=current_user)


@blueprint.route('/vypisy_vsichni/<string:mesic>', methods=['GET'])
@login_required
def vypisy_vsichni(mesic):
    # form = db.session.query( User.card_number.label('card_number'),User.full_name.label('fullname'),func.strftime('%Y-%m', Card.time).label("time"),\
    #                         func.strftime('%Y', Card.time).label("year"),func.strftime('%m', Card.time).label("month")).\
    #    join(Card,User.card_number==Card.card_number).group_by(func.strftime('%Y-%m', Card.time),User.full_name).\
    #    filter(func.strftime('%Y-%m', Card.time) == mesic).\
    #    order_by(User.full_name).all()
    form = db.session.query(User.card_number.label('card_number'), User.second_name.label('fullname'),
                            func.DATE_FORMAT(Card.time, '%Y-%m').label("time"), \
                            func.DATE_FORMAT(Card.time, '%Y').label("year"),
                            func.DATE_FORMAT(Card.time, '%m').label("month")). \
        join(Card, User.card_number == Card.card_number).group_by(func.DATE_FORMAT(Card.time, '%Y-%m'), User.second_name). \
        filter(func.DATE_FORMAT(Card.time, '%Y-%m') == mesic). \
        order_by(User.second_name).all()

    # form = db.session.query( User.card_number.label('card_number'),User.full_name.label('fullname'),func.strftime('%Y-%m', Card.time).label("time"),\
    #                         func.strftime('%Y', Card.time).label("year"),func.strftime('%m', Card.time).label("month"),\
    #                         Card.stravenky(User.card_number,func.strftime('%Y-%m', Card.time))).\
    #    join(Card,User.card_number==Card.card_number).group_by(func.strftime('%Y-%m', Card.time),User.full_name).\
    #    filter(func.strftime('%Y-%m', Card.time) == mesic).\
    #    order_by(User.full_name).all()
    # for a in form:
    #    print form.index(a)
    stravenka = []
    for u in form:
        data = pole_calendar(int(u[0]), int(u[3]), int(u[4]))
        stravenka.append([u[0], data['stravenka']])

    return render_template("auth/vypisy_vsichni.tmpl", stravenka=stravenka, form=form, user=current_user)


@blueprint.route('/vypisy', methods=['GET'])
@login_required
def vypisy():
    # form=Card.find_by_number(current_user.card_number)
    # form = db.session.query(Card.time).filter_by(card_number=current_user.card_number)
    form = db.session.query(func.DATE_FORMAT(Card.time, '%Y-%m').label("time"),
                            func.DATE_FORMAT(Card.time, '%Y').label("year"),
                            func.DATE_FORMAT(Card.time, '%m').label("month")).filter_by(
        card_number=current_user.card_number).group_by(func.DATE_FORMAT(Card.time, '%Y-%m'))
    # .group_by([func.day(Card.time)])

    return render_template("auth/vypisy.tmpl", form=form, data=current_user.chip_number, user=current_user)


@blueprint.route('/mesicni_vypis_vsichni/<string:mesic>', methods=['GET'])
@login_required
def mesicni_vypis_alluser(mesic):
    # form=Card.find_by_number(current_user.card_number)
    # form = db.session.query(Card.time).filter_by(card_number=current_user.card_number)
    form = db.session.query(func.strftime('%Y-%m-%d', Card.time).label("date"),
                            func.max(func.strftime('%H:%M', Card.time)).label("Max"), \
                            func.min(func.strftime('%H:%M', Card.time)).label("Min"),
                            (func.max(Card.time) - func.min(Card.time)).label("Rozdil")) \
        .filter(func.strftime('%Y-%-m', Card.time) == mesic).group_by(func.strftime('%Y-%m-%d', Card.time))
    # .group_by([func.day(Card.time)])
    return render_template("auth/mesicni_vypisy.tmpl", form=form, user=current_user)


@blueprint.route('/mesicni_vypis/<string:mesic>', methods=['GET'])
@login_required
def mesicni_vypis(mesic):
    # form=Card.find_by_number(current_user.card_number)
    # form = db.session.query(Card.time).filter_by(card_number=current_user.card_number)
    form = db.session.query(func.strftime('%Y-%m-%d', Card.time).label("date"),
                            func.max(func.strftime('%H:%M', Card.time)).label("Max"), \
                            func.min(func.strftime('%H:%M', Card.time)).label("Min"),
                            (func.max(Card.time) - func.min(Card.time)).label("Rozdil")) \
        .filter(
        (func.strftime('%Y-%-m', Card.time) == mesic) and (Card.card_number == current_user.card_number)).group_by(
        func.strftime('%Y-%m-%d', Card.time))
    # .group_by([func.day(Card.time)])
    return render_template("auth/mesicni_vypisy.tmpl", form=form, user=current_user)


from collections import OrderedDict


class DictSerializable(object):
    def _asdict(self):
        result = OrderedDict()
        for key in self.__mapper__.c.keys():
            result[key] = getattr(self, key)
        return result


@blueprint.route('/tbl_isdata/<int:od>/<int:do>', methods=['GET'])
@login_required
def tbl_insdata(od, do):
    # data = db.session.query( func.strftime('%Y-%m', Card.time).label("time")).filter_by(card_number=current_user.card_number).group_by(func.strftime('%Y-%m', Card.time))
    if od == 0 and do == 0:
        data = db.session.query(Card.id, Card.card_number, func.strftime('%Y-%m', Card.time).label("time")).all()
    else:
        data = db.session.query(Card.id, Card.card_number, func.strftime('%Y-%m', Card.time).label("time")).slice(od,
                                                                                                                  do)
    pole = ['id', 'time', 'card_number']
    result = [{col: getattr(d, col) for col in pole} for d in data]
    return jsonify(data=result)


@blueprint.route('/tabletest', methods=['GET'])
@login_required
def tabletest():
    return render_template('public/table.tmpl', user=current_user)


@blueprint.route('/caljsonr/<int:card_number>/<int:year>/<int:mount>', methods=['GET'])
@login_required
def caljson_edit(card_number, year, mount):
    lastday = last_day_of_month(year, mount)
    data = []
    startdate = '8:00'
    enddate = '16:00'
    for day in xrange(1, lastday):
        d = {}
        d['card_number'] = card_number
        d['day'] = day
        d['startdate'] = startdate
        d['enddate'] = enddate
        data.append(d)
    # print json.dumps(data, separators=(',',':'))

    # pole=['card_number','day','startdate','enddate']
    # result = [{col: d[col] for col in pole} for d in data]
    # print jsonify(data=result)



    # return render_template('auth/calendar.tmpl')
    return jsonify(data=data)


def pole_calendar(chip_number, year, month):
    lastday = last_day_of_month(year, month)
    datarow = []
    data = {}
    startdate = '0:00'
    enddate = '0:00'
    data['stravenka'] = 0
    # hodnota = list(db.session.query( func.strftime('%d', Card.time).label("den"),func.max(func.strftime('%H:%M', Card.time)).label("Max"),\
    #                         func.min(func.strftime('%H:%M', Card.time)).label("Min"))\
    #                        .filter(func.date(Card.time) == fromdate.date()).filter(Card.card_number == card_number).group_by(func.date(Card.time)))
    ff = datetime(year, month, 1).strftime('%Y-%m-%d')
    # hodnota = list(db.session.query( func.strftime('%d', Card.time).label("den"),func.max(func.strftime('%H:%M', Card.time)).label("Max"),\
    #                        func.min(func.strftime('%H:%M', Card.time)).label("Min"))\
    #                   .filter(Card.card_number == card_number).group_by(func.strftime('%Y-%m-%d', Card.time)))


    hodnota = list(db.session.query(extract('day', Card.time).label("den") \
                                    , func.min(func.DATE_FORMAT(Card.time, '%H:%i')).label("Min") \
                                    , func.max(func.DATE_FORMAT(Card.time, '%H:%i')).label("Max")) \
                   .filter(extract('month', Card.time) == month).filter(extract('year', Card.time) == year).filter(
        Card.chip_number == chip_number).group_by(func.DATE_FORMAT(Card.time, '%Y-%m-%d')))
    # .filter(datetime(Card.time).month == mounth  ))
    for day in xrange(1, lastday):
        d = {}
        d['day'] = day
        d['dow'] = datetime(year, month, day).weekday()
        datafromdb = filter(lambda x: x[0] == day, hodnota)
        if d['dow'] > 4:
            d['startdate'] = ''
            d['enddate'] = ''
        else:
            fromdate = datetime(year, month, day)
            todate = datetime(year, month, day) + timedelta(days=1)

            # hodnota = db.session.query( func.min(func.strftime('%H:%M', Card.time)).label("Min")).filter(Card.time >= fromdate).filter(Card.time < todate).filter(Card.card_number == card_number)
            # hodnota = list(db.session.query(func.date(Card.time).label('xxx')).filter(func.date(Card.time) == fromdate.date() ).filter(Card.card_number == card_number).all())
            # .filter(cast(Card.time,Date) == fromdate.date())
            # hodnota = list(db.session.query( func.strftime('%d', Card.time).label("den"),func.max(func.strftime('%H:%M', Card.time)).label("Max"),\
            #                func.min(func.strftime('%H:%M', Card.time)).label("Min"))\
            #               .filter(func.date(Card.time) == fromdate.date()).filter(Card.card_number == card_number).group_by(func.date(Card.time)))
            # .group_by(func.strftime('%Y-%m-%d', Card.time)))
            #            if len(hodnota) > 0 :
            #               print len(hodnota)

            d['startdate'] = startdate
            d['enddate'] = enddate
            if datafromdb:
                d['startdate'] = datafromdb[0][1]
                d['enddate'] = datafromdb[0][2]
            rozdil = datetime.strptime(d['enddate'], "%H:%M") - datetime.strptime(d['startdate'], "%H:%M")
            d['timespend'] = round(rozdil.total_seconds() / 3600, 2)
            if d['timespend'] >= 3:
                d['dost'] = 0
                data['stravenka'] = data['stravenka'] + 1
            else:
                d['dost'] = 1
        datarow.append(d)
    data['user'] = ''
    data['lastday'] = lastday
    data['mounth'] = month
    data['year'] = year
    data['chip_number'] = chip_number
    data['data'] = datarow

    return data


@blueprint.route('/calendar/<int:chip_number>/<int:year>/<int:month>', methods=['GET'])
@login_required
def calendar(chip_number, year, month):
    data = pole_calendar(chip_number, year, month)
    return render_template('auth/mesicni_vypis.tmpl', data=data, user=current_user)


@blueprint.route('/calendar_edit/<int:card_number>/<int:year>/<int:mounth>/<int:day>', methods=['GET', 'POST'])
@login_required
def calendar_edit(card_number, year, mounth, day):
    form = Editdate()
    form.den = str(day) + '-' + str(mounth) + '-' + str(year)
    form.card_number = str(card_number)
    if form.validate_on_submit():
        delday = db.session.query(Card).filter(extract('month', Card.time) == mounth).filter(
            extract('year', Card.time) == year).filter(extract('day', Card.time) == day).filter(
            Card.card_number == card_number)
        for item in delday:
            db.session.delete(item)
        time1 = str(day) + '-' + str(mounth) + '-' + str(year) + ' ' + str(form.data['startdate'])
        cas = datetime.strptime(time1, "%d-%m-%Y %H:%M:%S")
        i = Card(card_number=card_number, time=cas)
        db.session.add(i)
        time1 = str(day) + '-' + str(mounth) + '-' + str(year) + ' ' + str(form.data['enddate'])
        cas = datetime.strptime(time1, "%d-%m-%Y %H:%M:%S")
        i = Card(card_number=card_number, time=cas)
        db.session.add(i)
        db.session.commit()
        flash("Saved successfully", "info")
        return redirect('calendar/' + str(card_number) + '/' + str(year) + '/' + str(mounth))
    return render_template('auth/editdate.tmpl', form=form, user=current_user)


@blueprint.route('/user_list', methods=['GET'])
@login_required
def user_list():
    if current_user.access == "A" or current_user.access == "B":
        data = list(db.session.query(User).all())
        return render_template('auth/user_list.tmpl', data=data, user=current_user)
    else:
        flash("Access deny", "warn")
        return redirect('/')


@blueprint.route('/user_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def user_edit(id):
    # if current_user.email== "admin@iservery.com":
    user = db.session.query(User).get(id)
    if current_user.access <> 'A' and user.access == 'A':
        flash("Edit not allowed", "info")
        return redirect(request.args.get('next') or url_for('auth.user_list'))
    form = EditUserForm(obj=user)
    if current_user.access == "B":
        form.access.choices = [('U', 'User')]
    if form.validate_on_submit():
        new_user = user.update(**form.data)
        flash("Saved successfully", "info")
        return redirect(request.args.get('next') or url_for('auth.user_list'))
    return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)


@blueprint.route('/timecard_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def timecard_edit(id):
    timecard = db.session.query(Timecard).get(id)
    if current_user.access <> 'A':
        flash("Edit not allowed", "info")
        return redirect(request.args.get('next') or url_for('auth.user_list'))
    form = TimecardInsertForm(obj=timecard)
    if form.validate_on_submit():
        timecard.update(**form.data)
        flash("Saved successfully", "info")
        return redirect(request.args.get('next') or url_for('auth.show_timecards'))
    return render_template("auth/add_timecard.tmpl", form=form, user=current_user)


@blueprint.route('/timecard_del/<int:id>', methods=['GET', 'POST'])
@login_required
def timecard_del(id):
    if current_user.access <> 'A':
        flash("remove not allowed", "info")
        return redirect(request.args.get('next') or url_for('auth.user_list'))
    timecard = db.session.query(Timecard).filter_by(id=id).first()
    db.session.delete(timecard)
    db.session.commit()
    flash("Ctecka odstranena", "info")
    return redirect(request.args.get('next') or url_for('auth.show_timecards'))


@blueprint.route('/user_del/<int:id>', methods=['GET', 'POST'])
@login_required
def user_del(id):
    user = db.session.query(User).filter_by(id=id).first()
    group = db.session.query(User_has_group).filter_by(user_id=id).all()
    if current_user.access <> 'A' and user.access == 'A':
        flash("remove not allowed", "info")
        return redirect(request.args.get('next') or url_for('auth.user_list'))
    for o in group:
        db.session.delete(o)
    db.session.delete(user)
    db.session.commit()
    flash("User Removed", "info")
    return redirect(request.args.get('next') or url_for('auth.user_list'))


@blueprint.route('/group_del/<int:id>', methods=['GET', 'POST'])
@login_required
def group_del(id):
    if current_user.access <> 'A':
        flash("Remove not allowed", "info")
        return redirect(request.args.get('next') or url_for('auth.show_groups'))
    group = db.session.query(Group).filter_by(id=id).first()
    userGroups = db.session.query(User_has_group).filter_by(group_id=id).all()
    for o in userGroups:
        db.session.delete(o)
    timecardGroup = db.session.query(Group_has_timecard).filter_by(group_id=id).all()
    for o in timecardGroup:
        db.session.delete(o)
    db.session.delete(group)
    db.session.commit()
    flash("Group removed", "info")
    return redirect(request.args.get('next') or url_for('auth.show_groups'))


@blueprint.route('/group_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def group_edit(id):
    group = db.session.query(Group).get(id)
    if current_user.access <> 'A':
        flash("Edit not allowed", "info")
        return redirect(request.args.get('next') or url_for('auth.show_groups'))
    form = GroupInsertForm(obj=group)
    if form.validate_on_submit():
        group.update(**form.data)
        flash("Saved successfully", "info")
        return redirect(request.args.get('next') or url_for('auth.show_groups'))
    return render_template("auth/add_group.tmpl", form=form, user=current_user)


@blueprint.route('/userGroup_del/<int:id_uzivatele>/<int:id_skupiny>', methods=['GET', 'POST'])
@login_required
def userGroup_del(id_uzivatele, id_skupiny):
    if current_user.access <> 'A':
        flash("Remove not allowed", "info")
        return redirect(request.args.get('next') or url_for('auth.show_userGroups'))
    userGroups = db.session.query(User_has_group).filter_by(user_id=id_uzivatele, group_id=id_skupiny).all()
    for o in userGroups:
        db.session.delete(o)
    db.session.commit()
    flash("User has been removed from group", "info")
    return redirect(request.args.get('next') or url_for('auth.show_userGroups'))


@blueprint.route('/user_add/', methods=['GET', 'POST'])
@login_required
def user_add():
    if current_user.access == "A" or current_user.access == "B":
        form = EditUserForm()
        if current_user.access == "B":
            form.access.choices = [('U', 'User')]
        if form.validate_on_submit():
            if not username_is_available(form.username.data):
                flash("Username is not allowed use another", "warning")
                return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)
            if not email_is_available(form.email.data):
                flash("Email is used use another email", "warning")
                return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)

            new_user = User.create(**form.data)
            flash("Saved successfully", "info")
            return redirect(request.args.get('next') or url_for('auth.user_list'))

        return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)
    else:
        flash("Access Deny", "warn")
        return redirect(request.args.get('next') or url_for('public.index'))


@blueprint.route('/newmonth', methods=['GET', 'POST'])
@login_required
def newmonth():
    form = MonthInsert()
    if form.validate_on_submit():
        return redirect('/recreatemonth/' + form.month.data)
    return render_template('auth/recreatemonth.tmpl', form=form, user=current_user)


@blueprint.route('/recreatemonth/<string:month>', methods=['GET'])
@login_required
def createmonth(month):
    datum = datetime.strptime(month + '-1', "%Y-%m-%d")
    users = db.session.query(User).filter(Card.card_number <> '').all()
    for user in users:
        if not list(db.session.query(Card).filter(Card.card_number == user.card_number).filter(
                        func.DATE_FORMAT(Card.time, '%H:%M') == month)):
            i = Card(card_number=user.card_number, time=datum)
            db.session.add(i)
    db.session.commit()
    flash("Mesic vytvoren", "info")
    return redirect(request.args.get('next') or url_for('public.index'))


@blueprint.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = FileUploadForm()
    if form.validate_on_submit():
        data = request.files[form.filename.name].read()
        # filename = secure_filename(form.filename.data.filename)
        # file_path = os.path.join('./src/uploads/', filename)
        # open(file_path, 'w').write(data)
        if mujxmlparse(data):
            flash('Data nahrana', category='info')
    return render_template("auth/fileupload.tmpl", form=form, user=current_user)


@blueprint.route('/addGroup', methods=['GET', 'POST'])
@login_required
def groups():
    form = GroupInsertForm()

    if form.validate_on_submit():
        Group.create(**form.data)
        flash("Data uspesne pridana!", "info")
        return redirect('showGroup')
    return render_template("auth/add_group.tmpl", form=form, user=current_user)


@blueprint.route('/showGroup', methods=['GET', 'POST'])
@login_required
def show_groups():
    zaznamy = Group.getGroupList()
    return render_template("auth/showGroups.tmpl", data=zaznamy, user=current_user)


@blueprint.route('/addTimecard', methods=['GET', 'POST'])
@login_required
def timecards():
    form = TimecardInsertForm()

    if form.validate_on_submit():
        Timecard.create(**form.data)
        flash("Data uspesne pridana!", "info")
        return redirect('showTimecards')
    return render_template("auth/add_timecard.tmpl", form=form, user=current_user)


@blueprint.route('/showTimecards', methods=['GET', 'POST'])
@login_required
def show_timecards():
    zaznamy = Timecard.getTimecardList()
    return render_template("auth/showTimecards.tmpl", data=zaznamy, user=current_user)


@blueprint.route('/groupUsers', methods=['GET', 'POST'])
@login_required
def show_userGroups():
    zaznamy = User.user_in_group()
    data = []
    pom2 = ()
    for i in range(len(zaznamy)):
        pom = Group.getGroupName(zaznamy[i][3])
        pom2 = (zaznamy[i][0], zaznamy[i][1], zaznamy[i][2], pom, zaznamy[i][3])
        data.append(pom2)
    return render_template("auth/showUserGroups.tmpl", data=data, user=current_user)



@blueprint.route('/addToGroup', methods=['GET', 'POST'])
@login_required
def addToGroup():
    form = GroupForm()
    groups = Group.getIdName()
    form.groups.choices = groups
    if form.is_submitted():
        group_id = form.data['groups']
        for i in range(len(groups)):
            if group_id == str(groups[i][0]):
                group_name = str(groups[i][1])
        return redirect('addToGroup/' + group_id + '/' + group_name)
    return render_template("auth/user_has_group.tmpl", form=form, user=current_user)

@blueprint.route('/addToGroup/<int:id>/<string:name>', methods=['GET', 'POST'])
@login_required
def user_has_group_data(id, name):
    users = User.all_users()
    users_in_group = User_has_group.usersInGroup(id)
    form = AddUserToGroupForm()

    #fill form
    in_group = []
    no_group = []
    for i in range(len(users)):
        pom2 = ""
        boolean = True
        for j in range(len(users_in_group)):
            if(boolean):
                if(users[i][0] == users_in_group[j][0]):
                    pom2 = users[i][2]+" "+ users[i][1]
                    pom3 = (users[i][0], pom2)
                    in_group.append(pom3)
                    boolean = False
        if(boolean != False):
            pom2 = users[i][2] + " " + users[i][1]
            pom3 = (users[i][0], pom2)
            no_group.append(pom3)
    form.select_group.choices = in_group
    form.select_user.choices = no_group
    #fill end

    if form.is_submitted():
        group_id = id
        select_user = form.data['select_user']
        select_group = form.data['select_group']
        for i in range(len(select_user)):
            for j in range(len(in_group)):
                if str(select_user[i]) == str(in_group[j][0]):
                    User_has_group.findToDelete(select_user[i], group_id)
        for i in range(len(select_group)):
            for j in range(len(no_group)):
                if str(select_group[i]) == str(no_group[j][0]):
                    pom2 = User_has_group(select_group[i], group_id)
                    db.session.add(pom2)
        db.session.commit()
        flash("Data zaznamenana!", "info")
        return redirect('groupUsers')

    return render_template("auth/user_has_group_id.tmpl", form=form, user=current_user, name=name)



@blueprint.route('/pristupy', methods=['GET', 'POST'])
@login_required
def pristupy():
    carddata = Card.getAllByUserId(current_user.id)
    data = []
    pom = ()
    for i in range(len(carddata)):
        timecard_name = Timecard.getName(carddata[i][1])
        if carddata[i][2] == "0":
            pom = (carddata[i][0], timecard_name[0], "Ne")
        else:
            pom = (carddata[i][0], timecard_name[0], "Ano")
        data.append(pom)
    return render_template("auth/pristupy.tmpl", data=data, user=current_user)


@blueprint.route('/vsechny_pristupy', methods=['GET', 'POST'])
@login_required
def pristupy_all():
    carddata = Card.getAll()
    data = []
    pom = ()
    for i in range(len(carddata)):
        timecard_name = Timecard.getName(carddata[i][2])
        if carddata[i][3] == 0:
            user = "Neznamy"
        else:
            userPom = User.findUserById(carddata[i][3])
            user = str(userPom[0][1]) + " " + str(userPom[0][2])

        if carddata[i][4] == "0":
            pom = (carddata[i][0], carddata[i][1], timecard_name[0], user, "Ne")
        else:
            pom = (carddata[i][0], carddata[i][1], timecard_name[0], user, "Ano")
        data.append(pom)
    data = sorted(data, key=lambda zaznam: zaznam[3])   #########################################################################################################
    return render_template("auth/pristupy_all.tmpl", data=data, user=current_user)

@blueprint.route('/new_user/<string:chip>', methods=['GET', 'POST'])
@login_required
def new_user(chip):
    if current_user.access <> 'A':
            flash("Remove not allowed", "info")
            return redirect(request.args.get('next') or url_for('auth.show_userGroups'))
    form = EditUserForm()
    form.chip_number.data = chip
    if form.validate_on_submit():
        User.create(**form.data)
        flash("User added successfully", "info")
        return redirect(request.args.get('next') or url_for('auth.user_list'))
    return render_template("auth/editAccountAdmin.tmpl", form=form, user=current_user)



@blueprint.route('/skupiny', methods=['GET', 'POST'])
@login_required
def skupiny():
    in_groups = User_has_group.compareUsers(current_user.id)
    data = []
    pom_jmeno = []
    pom2 = []
    for i in range(len(in_groups)):
        timecard_id = Group_has_timecard.findTimecard(in_groups[i][0])
        time_from = Group.getTimeFrom(in_groups[i][0])
        time_to = Group.getTimeTo(in_groups[i][0])
        for j in range(len(timecard_id)):
            if timecard_id[j] is None:
                print "nic"
            jmeno = Timecard.getName(timecard_id[j][0])
            pom = (jmeno[0], time_from, time_to)

            if i > 0:
                for k in range(len(data)):
                    boolean = True
                    if str(data[k][0]) == str(jmeno[0]):
                        boolean = False
                        if pom[1] < data[k][1]:
                            print str(pom[1]) +">"+ str(data[k][1])
                            data[k][1].append(pom[1])
                        if pom[2] > data[k][2]:
                            print str(pom[2]) +">"+ str(data[k][2])
                            data[k][2].append(pom[2])
                    if boolean:
                        data.append(pom)
            else:
                data.append(pom)
    return render_template("auth/user_skupiny.tmpl", data=data, user=current_user)

@blueprint.route('/assign_timecard', methods=['GET', 'POST'])
@login_required
def timecardForGroup():
    form = GroupForm()
    groups = Group.getIdName()
    form.groups.choices = groups
    if form.is_submitted():
        group_id = form.data['groups']
        for i in range(len(groups)):
            if group_id == str(groups[i][0]):
                group_name = str(groups[i][1])
        return redirect('add_timecard_to_group/' + group_id + '/' + group_name)
    return render_template("auth/group_has_timecard.tmpl", form=form, user=current_user)


@blueprint.route('/assign_timecard_to_group/<int:id>/<string:name>', methods=['GET', 'POST'])
@login_required
def group_has_timecard_data(id, name):
    timecards = Timecard.getIdName()
    group_has_timecard = Group_has_timecard.findTimecard(id)
    form = AssignTimecardForm()
    """
    #fill form
    in_group = []
    no_group = []
    for i in range(len(timecards)):
        pom2 = ""
        boolean = True
        for j in range(len(group_has_timecard)):
            if(boolean):
                if(timecards[i][0] == group_has_timecard[j][0]):
                    pom2 = timecards[i][1]+" "+timecards[i][2]
                    pom3 = (timecards[i][0], pom2)
                    in_group.append(pom3)
                    boolean = False
        if(boolean != False):
            pom2 = str(timecards[i][1]) + " " + str(timecards[i][2])
            pom3 = (timecards[i][0], pom2)
            no_group.append(pom3)
    form.select_group.choices = in_group
    form.select_user.choices = no_group
    #fill end
    ""
    if form.is_submitted():
        group_id = id
        select_user = form.data['select_user']
        select_group = form.data['select_group']
        for i in range(len(select_user)):
            for j in range(len(in_group)):
                if str(select_user[i]) == str(in_group[j][0]):
                    User_has_group.findToDelete(select_user[i], group_id)
        for i in range(len(select_group)):
            for j in range(len(no_group)):
                if str(select_group[i]) == str(no_group[j][0]):
                    pom2 = Group_has_timecard(select_group[i], group_id)
                    db.session.add(pom2)
        flash("Data zaznamenana!", "info")
        return redirect('groupUsers')
        """
    return render_template("auth/user_has_group_id.tmpl", form=form, user=current_user, name=name)
