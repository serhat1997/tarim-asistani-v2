from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .models import PasswordResetCode, UserProfile

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'Şifreler eşleşmiyor!')
            return render(request, 'accounts/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Bu kullanıcı adı zaten kullanılıyor!')
            return render(request, 'accounts/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Bu email zaten kayıtlı!')
            return render(request, 'accounts/register.html')

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, 'Kayıt başarılı! Lütfen giriş yapınız.')
        return redirect('login')

    return render(request, 'accounts/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def about_view(request):
    return render(request, 'accounts/about.html')

def blog_view(request):
    return render(request, 'accounts/blog.html')

def contact_view(request):
    return render(request, 'accounts/contact.html')

@login_required
def user_list_view(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    users = User.objects.all().order_by('username')
    return render(request, 'accounts/users.html', {
        'users': users,
        'logged_user_name': request.user.username,
    })

@login_required
def user_suspend_view(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user.pk != request.user.pk:
            user.is_active = not user.is_active
            user.save()
            status = "askıya alındı" if not user.is_active else "aktif edildi"
            messages.success(request, f'"{user.username}" kullanıcısı {status}.')
        else:
            messages.error(request, 'Kendi hesabınızı askıya alamazsınız.')
    return redirect('user_list')

@login_required
def user_change_password_admin_view(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        password = request.POST.get('new_password', '')
        password2 = request.POST.get('new_password2', '')
        if len(password) < 6:
            messages.error(request, f'"{user.username}" için şifre en az 6 karakter olmalıdır.')
        elif password != password2:
            messages.error(request, 'Şifreler eşleşmiyor.')
        else:
            user.set_password(password)
            user.save()
            messages.success(request, f'"{user.username}" kullanıcısının şifresi başarıyla güncellendi.')
    return redirect('user_list')


@login_required
def user_delete_admin_view(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user.pk != request.user.pk:
            username = user.username
            user.delete()
            messages.success(request, f'"{username}" kullanıcısı silindi.')
        else:
            messages.error(request, 'Kendi hesabınızı bu sayfadan silemezsiniz.')
    return redirect('user_list')

def _find_user_by_email_or_phone(value):
    value = value.strip()
    user = User.objects.filter(email__iexact=value).first()
    if user:
        return user, 'email'
    profile = UserProfile.objects.filter(phone=value).first()
    if profile:
        return profile.user, 'phone'
    return None, None


def _send_reset_code(user, method, reset_obj):
    code = reset_obj.code
    if method == 'email':
        send_mail(
            subject='Şifre Sıfırlama Kodunuz',
            message=(
                f'Merhaba {user.username},\n\n'
                f'Şifre sıfırlama kodunuz: {code}\n\n'
                f'Bu kod 10 dakika geçerlidir. Eğer bu isteği siz yapmadıysanız dikkate almayınız.'
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    else:
        # SMS entegrasyonu yapılandırılmamış; geliştirme ortamında konsola yazdırılır.
        profile = getattr(user, 'profile', None)
        phone = profile.phone if profile else '—'
        print(f"\n{'='*40}\nSMS (simülasyon) → {phone}\nKod: {code}\n{'='*40}\n")


def forgot_password_view(request):
    if request.method == 'POST':
        value = request.POST.get('contact', '').strip()
        if not value:
            return render(request, 'accounts/forgot_password.html',
                          {'step': 1, 'error': 'Lütfen e-posta veya telefon numarası girin.'})

        user, method = _find_user_by_email_or_phone(value)
        if not user:
            return render(request, 'accounts/forgot_password.html',
                          {'step': 1, 'error': 'Bu bilgiye ait kayıtlı hesap bulunamadı.'})

        reset_obj = PasswordResetCode.create_for(user)
        _send_reset_code(user, method, reset_obj)

        masked = value[:2] + '*' * (len(value) - 4) + value[-2:] if len(value) > 4 else '****'
        return render(request, 'accounts/forgot_password.html', {
            'step': 2,
            'token': reset_obj.token,
            'masked': masked,
            'method': method,
        })

    return render(request, 'accounts/forgot_password.html', {'step': 1})


def verify_reset_code_view(request, token):
    reset_obj = get_object_or_404(PasswordResetCode, token=token)

    if not reset_obj.is_valid():
        return render(request, 'accounts/forgot_password.html',
                      {'step': 1, 'error': 'Kodun süresi dolmuş. Lütfen tekrar deneyin.'})

    if request.method == 'POST':
        entered = request.POST.get('code', '').strip()
        if entered == reset_obj.code:
            return redirect('reset_password', token=token)
        return render(request, 'accounts/forgot_password.html', {
            'step': 2, 'token': token,
            'error': 'Girdiğiniz kod hatalı.',
        })

    return render(request, 'accounts/forgot_password.html', {'step': 2, 'token': token})


def reset_password_view(request, token):
    reset_obj = get_object_or_404(PasswordResetCode, token=token)

    if not reset_obj.is_valid():
        return render(request, 'accounts/forgot_password.html',
                      {'step': 1, 'error': 'Bağlantı süresi dolmuş. Lütfen tekrar deneyin.'})

    if request.method == 'POST':
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        if len(password) < 6:
            return render(request, 'accounts/forgot_password.html',
                          {'step': 3, 'token': token, 'error': 'Şifre en az 6 karakter olmalıdır.'})
        if password != password2:
            return render(request, 'accounts/forgot_password.html',
                          {'step': 3, 'token': token, 'error': 'Şifreler eşleşmiyor.'})

        user = reset_obj.user
        user.set_password(password)
        user.save()
        reset_obj.is_used = True
        reset_obj.save()
        messages.success(request, 'Şifreniz başarıyla güncellendi. Giriş yapabilirsiniz.')
        return redirect('login')

    return render(request, 'accounts/forgot_password.html', {'step': 3, 'token': token})


@login_required
def account_delete_view(request):
    if request.method == 'POST':
        confirm = request.POST.get('confirm')
        if confirm == 'SIL':
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, 'Hesabınız başarıyla silindi.')
            return redirect('login')
        else:
            messages.error(request, 'Onay metni hatalı. Hesabınız silinmedi.')
            return redirect('account_delete')
    return render(request, 'accounts/account_delete_confirm.html', {
        'logged_user_name': request.user.username,
    })
