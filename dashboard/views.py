from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from transactions.models import Transaction
from customers.models import Customer
from .models import PaymentPlan, CustomerPayment

@login_required
def dashboard(request):
    # Admin tüm işlemleri görebilir, normal kullanıcılar sadece kendilerinkileri
    if request.user.is_staff:
        transactions = Transaction.objects.all()
    else:
        transactions = Transaction.objects.filter(user=request.user)
    
    total_sales = transactions.filter(type='sale').aggregate(Sum('amount'))['amount__sum'] or 0
    total_purchases = transactions.filter(type='purchase').aggregate(Sum('amount'))['amount__sum'] or 0
    profit = total_sales - total_purchases

    def format_turkish_number(value):
        formatted = f"{value:,.2f}"
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')

    recent_transactions = transactions.order_by('-date', '-id')[:10]

    return render(request, 'dashboard/dashboard.html', {
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'profit': profit,
        'formatted_total_sales': format_turkish_number(total_sales),
        'formatted_total_purchases': format_turkish_number(total_purchases),
        'formatted_profit': format_turkish_number(profit),
        'greeting': f"Merhaba {request.user.first_name or request.user.get_full_name() or request.user.username} Hoş Geldin 👋",
        'logged_user_name': request.user.username,
        'recent_transactions': recent_transactions,
    })

@login_required
def statement(request):
    def fmt(v):
        return f"{v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    if request.user.is_staff:
        customers = Customer.objects.all().order_by('name')
    else:
        customers = Customer.objects.filter(user=request.user).order_by('name')

    selected_customer = None
    entries = []
    summary = {}
    net_balance_raw = Decimal('0')

    customer_id = request.GET.get('customer')
    if customer_id:
        try:
            if request.user.is_staff:
                selected_customer = Customer.objects.get(id=customer_id)
            else:
                selected_customer = Customer.objects.get(id=customer_id, user=request.user)

            txn_qs = Transaction.objects.filter(customer=selected_customer).order_by('date', 'id')
            pay_qs = CustomerPayment.objects.filter(customer=selected_customer).order_by('date', 'id')

            raw_sales     = txn_qs.filter(type='sale').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            raw_purchases = txn_qs.filter(type='purchase').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            raw_received  = pay_qs.filter(direction='alindi').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            raw_paid_out  = pay_qs.filter(direction='odendi').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            net_balance_raw = raw_sales - raw_purchases - raw_received + raw_paid_out

            summary = {
                'sales':     fmt(raw_sales),
                'purchases': fmt(raw_purchases),
                'received':  fmt(raw_received),
                'paid_out':  fmt(raw_paid_out),
                'net':       fmt(abs(net_balance_raw)),
                'net_raw':   net_balance_raw,
            }

            for t in txn_qs:
                entries.append({
                    'pk':           t.pk,
                    'date':         t.date,
                    'kind':         t.type,
                    'label':        'Satış' if t.type == 'sale' else 'Alış',
                    'detail':       f"{t.get_product_display()} · {t.quantity} {t.get_unit_display()}",
                    'amount_raw':   t.amount,
                    'amount':       fmt(t.amount),
                    'reference_no': t.reference_no,
                    'description':  t.description,
                    'sign':         Decimal('1') if t.type == 'sale' else Decimal('-1'),
                    'delete_type':  'transaction',
                })

            for cp in pay_qs:
                entries.append({
                    'pk':           cp.pk,
                    'date':         cp.date,
                    'kind':         'payment_' + cp.direction,
                    'label':        'Tahsilat' if cp.direction == 'alindi' else 'Ödeme',
                    'detail':       cp.get_payment_type_display(),
                    'amount_raw':   cp.amount,
                    'amount':       fmt(cp.amount),
                    'reference_no': cp.reference_no,
                    'description':  cp.description,
                    'sign':         Decimal('-1') if cp.direction == 'alindi' else Decimal('1'),
                    'delete_type':  'payment',
                })

            entries.sort(key=lambda x: x['date'])

            running = Decimal('0')
            for e in entries:
                running += e['sign'] * e['amount_raw']
                e['balance_raw'] = running
                e['balance']     = fmt(abs(running))
                e['balance_pos'] = running >= 0

            entries.reverse()

        except Customer.DoesNotExist:
            pass

    return render(request, 'dashboard/statement.html', {
        'customers':         customers,
        'selected_customer': selected_customer,
        'entries':           entries,
        'summary':           summary,
        'net_balance_raw':   net_balance_raw,
        'logged_user_name':  request.user.username,
    })

@login_required
def payments(request):
    def fmt(value):
        return f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    if request.user.is_staff:
        plans = PaymentPlan.objects.all().order_by('-created_at')
        cp_list = CustomerPayment.objects.all().order_by('-date', '-created_at')
    else:
        plans = PaymentPlan.objects.filter(user=request.user).order_by('-created_at')
        cp_list = CustomerPayment.objects.filter(user=request.user).order_by('-date', '-created_at')

    for plan in plans:
        plan.formatted_amount = fmt(plan.amount)
    for cp in cp_list:
        cp.formatted_amount = fmt(cp.amount)

    return render(request, 'dashboard/payments.html', {
        'plans': plans,
        'cp_list': cp_list,
        'logged_user_name': request.user.username,
    })


@login_required
def customer_payment_create(request):
    errors = []
    preselected_customer = request.GET.get('customer', '')
    form_data = {
        'customer': request.POST.get('customer', preselected_customer),
        'direction': request.POST.get('direction', ''),
        'payment_type': request.POST.get('payment_type', ''),
        'amount': request.POST.get('amount', ''),
        'date': request.POST.get('date', ''),
        'reference_no': request.POST.get('reference_no', ''),
        'description': request.POST.get('description', ''),
    }

    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        direction = request.POST.get('direction')
        payment_type = request.POST.get('payment_type')
        amount_text = request.POST.get('amount', '0').strip().replace('₺', '').replace(' ', '')
        date = request.POST.get('date') or None
        reference_no = request.POST.get('reference_no', '').strip()
        description = request.POST.get('description', '')

        if not customer_id:
            errors.append('Cari seçimi zorunludur.')
        if not direction:
            errors.append('Yön seçimi zorunludur.')
        if not payment_type:
            errors.append('Ödeme türü seçilmelidir.')
        if not date:
            errors.append('Tarih zorunludur.')

        if amount_text.count(',') and amount_text.count('.'):
            amount_text = amount_text.replace('.', '').replace(',', '.')
        else:
            amount_text = amount_text.replace(',', '.')

        try:
            amount = Decimal(amount_text or '0')
            if amount <= 0:
                errors.append('Tutar sıfırdan büyük olmalıdır.')
        except (InvalidOperation, ValueError):
            errors.append('Geçerli bir tutar girin.')
            amount = Decimal('0')

        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                errors.append('Seçilen cari bulunamadı.')

        if customer and not request.user.is_staff and customer.user != request.user:
            return redirect('dashboard')

        if not errors and customer:
            CustomerPayment.objects.create(
                user=request.user,
                customer=customer,
                direction=direction,
                payment_type=payment_type,
                amount=amount,
                date=date,
                reference_no=reference_no,
                description=description,
            )
            return redirect('payments')

        for error in errors:
            messages.error(request, error)

    if request.user.is_staff:
        customers = Customer.objects.all()
    else:
        customers = Customer.objects.filter(user=request.user)

    return render(request, 'dashboard/customer_payment_form.html', {
        'customers': customers,
        'form_data': form_data,
    })

@login_required
def payment_create(request):
    errors = []
    form_data = {
        'customer': request.POST.get('customer', ''),
        'plan_type': request.POST.get('plan_type', ''),
        'payment_category': request.POST.get('payment_category', ''),
        'installments': request.POST.get('installments', '1'),
        'amount': request.POST.get('amount', ''),
        'due_date': request.POST.get('due_date', ''),
        'description': request.POST.get('description', ''),
    }

    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        plan_type = request.POST.get('plan_type')
        payment_category = request.POST.get('payment_category')
        installments_text = request.POST.get('installments', '1')
        amount_text = request.POST.get('amount', '0')
        due_date = request.POST.get('due_date') or None
        description = request.POST.get('description', '')

        if not customer_id:
            errors.append('Cari seçimi zorunludur.')
        if not plan_type:
            errors.append('Plan türü seçilmelidir.')
        if not payment_category:
            errors.append('Ödeme kategorisi seçilmelidir.')

        try:
            installments = int(installments_text or 1)
            if installments < 1:
                raise ValueError()
        except ValueError:
            errors.append('Taksit sayısı için geçerli bir sayı girin.')
            installments = 1

        normalized_amount = amount_text.strip().replace('₺', '').replace(' ', '')
        if normalized_amount.count(',') and normalized_amount.count('.'):
            normalized_amount = normalized_amount.replace('.', '').replace(',', '.')
        else:
            normalized_amount = normalized_amount.replace(',', '.')

        try:
            amount = Decimal(normalized_amount or '0')
            if amount <= 0:
                errors.append('Tutar sıfırdan büyük olmalıdır.')
        except (InvalidOperation, ValueError):
            errors.append('Geçerli bir tutar girin.')
            amount = Decimal('0')

        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                errors.append('Seçilen cari bulunamadı.')

        if customer and not request.user.is_staff and customer.user != request.user:
            return redirect('dashboard')

        if not errors and customer:
            PaymentPlan.objects.create(
                user=request.user,
                customer=customer,
                plan_type=plan_type,
                payment_category=payment_category,
                installments=installments,
                amount=amount,
                due_date=due_date,
                description=description,
            )
            return redirect('payments')

        for error in errors:
            messages.error(request, error)

    if request.user.is_staff:
        customers = Customer.objects.all()
    else:
        customers = Customer.objects.filter(user=request.user)

    return render(request, 'dashboard/payment_form.html', {
        'customers': customers,
        'form_data': form_data,
    })


@login_required
def customer_payment_delete(request, pk):
    cp = get_object_or_404(CustomerPayment, pk=pk)
    if not request.user.is_staff and cp.user != request.user:
        raise Http404
    if request.method == 'POST':
        cp.delete()
        next_url = request.POST.get('next', '')
        if next_url:
            return redirect(next_url)
    return redirect('payments')


@login_required
def payment_plan_delete(request, pk):
    plan = get_object_or_404(PaymentPlan, pk=pk)
    if not request.user.is_staff and plan.user != request.user:
        raise Http404
    if request.method == 'POST':
        plan.delete()
    return redirect('payments')
