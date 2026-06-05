from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from datetime import date as dt_date, timedelta
from transactions.models import Transaction
from customers.models import Customer
from .models import PaymentPlan, CustomerPayment
from .utils import fmt_tr

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

    recent_transactions = transactions.order_by('-date', '-id')[:10]

    return render(request, 'dashboard/dashboard.html', {
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'profit': profit,
        'formatted_total_sales': fmt_tr(total_sales),
        'formatted_total_purchases': fmt_tr(total_purchases),
        'formatted_profit': fmt_tr(profit),
        'greeting': f"Merhaba {request.user.first_name or request.user.get_full_name() or request.user.username} Hoş Geldin 👋",
        'logged_user_name': request.user.username,
        'recent_transactions': recent_transactions,
    })

@login_required
def statement(request):
    fmt = fmt_tr

    if request.user.is_staff:
        customers = Customer.objects.all().order_by('name')
    else:
        customers = Customer.objects.filter(user=request.user).order_by('name')

    selected_customer = None
    entries = []
    summary = {}
    net_balance_raw = Decimal('0')

    customer_id      = request.GET.get('customer', '').strip()
    date_from_raw    = request.GET.get('date_from', '').strip()
    date_to_raw      = request.GET.get('date_to', '').strip()
    period           = request.GET.get('period', '').strip()
    product_filter   = request.GET.get('product', '').strip()
    islem_turu       = request.GET.getlist('islem_turu')

    # Dönem seçimi tarih aralığına dönüştürülür
    today = dt_date.today()
    eff_from = date_from_raw
    eff_to   = date_to_raw
    if period:
        eff_from = eff_to = ''
        if period == 'bu_ay':
            eff_from = today.replace(day=1).isoformat()
            eff_to   = today.isoformat()
        elif period == 'gecen_ay':
            first_this = today.replace(day=1)
            last_prev  = first_this - timedelta(days=1)
            eff_from   = last_prev.replace(day=1).isoformat()
            eff_to     = last_prev.isoformat()
        elif period == 'bu_yil':
            eff_from = today.replace(month=1, day=1).isoformat()
            eff_to   = today.isoformat()
        elif period == 'gecen_yil':
            eff_from = today.replace(year=today.year - 1, month=1, day=1).isoformat()
            eff_to   = today.replace(year=today.year - 1, month=12, day=31).isoformat()
        elif period == 'son_7_gun':
            eff_from = (today - timedelta(days=7)).isoformat()
            eff_to   = today.isoformat()
        elif period == 'son_30_gun':
            eff_from = (today - timedelta(days=30)).isoformat()
            eff_to   = today.isoformat()
        elif period == 'son_90_gun':
            eff_from = (today - timedelta(days=90)).isoformat()
            eff_to   = today.isoformat()

    if customer_id:
        try:
            if request.user.is_staff:
                selected_customer = Customer.objects.get(id=customer_id)
            else:
                selected_customer = Customer.objects.get(id=customer_id, user=request.user)

            txn_qs = Transaction.objects.filter(customer=selected_customer).order_by('date', 'id')
            pay_qs = CustomerPayment.objects.filter(customer=selected_customer).order_by('date', 'id')

            # Tarih filtresi
            if eff_from:
                txn_qs = txn_qs.filter(date__gte=eff_from)
                pay_qs = pay_qs.filter(date__gte=eff_from)
            if eff_to:
                txn_qs = txn_qs.filter(date__lte=eff_to)
                pay_qs = pay_qs.filter(date__lte=eff_to)

            # Ürün filtresi (sadece işlemlere)
            if product_filter:
                txn_qs = txn_qs.filter(product=product_filter)

            # İşlem türü filtresi
            if islem_turu:
                txn_types = [t for t in ('sale', 'purchase') if t in islem_turu]
                pay_dirs  = [d for k, d in (('payment_alindi', 'alindi'), ('payment_odendi', 'odendi')) if k in islem_turu]
                txn_qs = txn_qs.filter(type__in=txn_types) if txn_types else txn_qs.none()
                pay_qs = pay_qs.filter(direction__in=pay_dirs) if pay_dirs else pay_qs.none()

            raw_sales     = txn_qs.filter(type='sale').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            raw_purchases = txn_qs.filter(type='purchase').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            raw_received  = pay_qs.filter(direction='alindi').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            raw_paid_out  = pay_qs.filter(direction='odendi').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            net_balance_raw = raw_sales - raw_purchases - raw_received + raw_paid_out

            unit_labels = dict(Transaction.UNIT_CHOICES)

            def fmt_qty(qs, txn_type):
                rows = qs.filter(type=txn_type).values('unit').annotate(total=Sum('quantity')).order_by('unit')
                parts = []
                for row in rows:
                    val = row['total']
                    if val:
                        fv = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        if fv.endswith(',00'):
                            fv = fv[:-3]
                        parts.append(f"{fv} {unit_labels.get(row['unit'], row['unit'])}")
                return ' · '.join(parts) if parts else None

            summary = {
                'sales':        fmt(raw_sales),
                'purchases':    fmt(raw_purchases),
                'received':     fmt(raw_received),
                'paid_out':     fmt(raw_paid_out),
                'net':          fmt(abs(net_balance_raw)),
                'net_raw':      net_balance_raw,
                'sale_qty':     fmt_qty(txn_qs, 'sale'),
                'purchase_qty': fmt_qty(txn_qs, 'purchase'),
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

    # Ürün listesi (tekrar eden 'diger' temizlenir)
    seen, all_products = set(), []
    for val, label in Transaction.SALE_PRODUCTS + Transaction.PURCHASE_PRODUCTS:
        if val not in seen:
            seen.add(val)
            all_products.append((val, label))

    period_labels = {
        'bu_ay': 'Bu Ay', 'gecen_ay': 'Geçen Ay',
        'bu_yil': 'Bu Yıl', 'gecen_yil': 'Geçen Yıl',
        'son_7_gun': 'Son 7 Gün', 'son_30_gun': 'Son 30 Gün', 'son_90_gun': 'Son 90 Gün',
    }
    product_map = dict(Transaction.SALE_PRODUCTS + Transaction.PURCHASE_PRODUCTS)
    islem_map   = {'sale': 'Satış', 'purchase': 'Alış', 'payment_alindi': 'Tahsilat', 'payment_odendi': 'Ödeme'}

    is_filtered = bool(date_from_raw or date_to_raw or period or product_filter or islem_turu)

    return render(request, 'dashboard/statement.html', {
        'customers':              customers,
        'selected_customer':      selected_customer,
        'entries':                entries,
        'summary':                summary,
        'net_balance_raw':        net_balance_raw,
        'logged_user_name':       request.user.username,
        # Filtre durumu
        'filter_date_from':       date_from_raw,
        'filter_date_to':         date_to_raw,
        'filter_period':          period,
        'filter_product':         product_filter,
        'filter_islem_turu':      islem_turu,
        'all_products':           all_products,
        'is_filtered':            is_filtered,
        'filter_period_label':    period_labels.get(period, ''),
        'filter_product_label':   product_map.get(product_filter, ''),
        'filter_islem_labels':    [islem_map[t] for t in islem_turu if t in islem_map],
    })

@login_required
def statement_export(request):
    """Aktif ekstre filtresini Excel dosyasına aktar."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, numbers
    from openpyxl.utils import get_column_letter

    # statement view'ındaki filtre mantığının kopyası (tek kaynak haline getirmek için refactor edilebilir)
    customer_id    = request.GET.get('customer', '').strip()
    date_from_raw  = request.GET.get('date_from', '').strip()
    date_to_raw    = request.GET.get('date_to', '').strip()
    period         = request.GET.get('period', '').strip()
    product_filter = request.GET.get('product', '').strip()
    islem_turu     = request.GET.getlist('islem_turu')

    today = dt_date.today()
    eff_from = date_from_raw
    eff_to   = date_to_raw
    period_map = {
        'bu_ay':     (today.replace(day=1),                         today),
        'gecen_ay':  ((today.replace(day=1) - timedelta(days=1)).replace(day=1),
                      today.replace(day=1) - timedelta(days=1)),
        'bu_yil':    (today.replace(month=1, day=1),                today),
        'gecen_yil': (today.replace(year=today.year-1, month=1, day=1),
                      today.replace(year=today.year-1, month=12, day=31)),
        'son_7_gun': (today - timedelta(days=7),                    today),
        'son_30_gun':(today - timedelta(days=30),                   today),
        'son_90_gun':(today - timedelta(days=90),                   today),
    }
    if period and period in period_map:
        eff_from = period_map[period][0].isoformat()
        eff_to   = period_map[period][1].isoformat()

    if not customer_id:
        return redirect('statement')
    try:
        if request.user.is_staff:
            customer = Customer.objects.get(id=customer_id)
        else:
            customer = Customer.objects.get(id=customer_id, user=request.user)
    except Customer.DoesNotExist:
        return redirect('statement')

    txn_qs = Transaction.objects.filter(customer=customer).order_by('date', 'id')
    pay_qs = CustomerPayment.objects.filter(customer=customer).order_by('date', 'id')
    if eff_from:
        txn_qs = txn_qs.filter(date__gte=eff_from); pay_qs = pay_qs.filter(date__gte=eff_from)
    if eff_to:
        txn_qs = txn_qs.filter(date__lte=eff_to);   pay_qs = pay_qs.filter(date__lte=eff_to)
    if product_filter:
        txn_qs = txn_qs.filter(product=product_filter)
    if islem_turu:
        txn_types = [t for t in ('sale', 'purchase') if t in islem_turu]
        pay_dirs  = [d for k, d in (('payment_alindi', 'alindi'), ('payment_odendi', 'odendi')) if k in islem_turu]
        txn_qs = txn_qs.filter(type__in=txn_types) if txn_types else txn_qs.none()
        pay_qs = pay_qs.filter(direction__in=pay_dirs) if pay_dirs else pay_qs.none()

    entries = []
    for t in txn_qs:
        entries.append({
            'date': t.date, 'label': 'Satış' if t.type == 'sale' else 'Alış',
            'detail': f"{t.get_product_display()} · {t.quantity} {t.get_unit_display()}",
            'amount': t.amount, 'sign': Decimal('1') if t.type == 'sale' else Decimal('-1'),
            'reference_no': t.reference_no, 'description': t.description,
        })
    for cp in pay_qs:
        entries.append({
            'date': cp.date, 'label': 'Tahsilat' if cp.direction == 'alindi' else 'Ödeme',
            'detail': cp.get_payment_type_display(), 'amount': cp.amount,
            'sign': Decimal('-1') if cp.direction == 'alindi' else Decimal('1'),
            'reference_no': cp.reference_no, 'description': cp.description,
        })
    entries.sort(key=lambda x: x['date'])
    running = Decimal('0')
    for e in entries:
        running += e['sign'] * e['amount']
        e['balance'] = running
    entries.reverse()

    # Excel oluştur
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ekstre"

    hdr_font  = Font(bold=True, color='FFFFFF')
    hdr_fill  = PatternFill(fill_type='solid', fgColor='3B82F6')
    center    = Alignment(horizontal='center', vertical='center')

    headers = ['Tarih', 'Tür', 'Detay', 'Tutar (₺)', 'Bakiye (₺)', 'Ref / Belge No', 'Açıklama']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font; cell.fill = hdr_fill; cell.alignment = center

    for row_idx, e in enumerate(entries, 2):
        ws.cell(row=row_idx, column=1, value=str(e['date']))
        ws.cell(row=row_idx, column=2, value=e['label'])
        ws.cell(row=row_idx, column=3, value=e['detail'])
        amt_cell = ws.cell(row=row_idx, column=4, value=float(e['amount']))
        amt_cell.number_format = '#,##0.00'
        bal_cell = ws.cell(row=row_idx, column=5, value=float(e['balance']))
        bal_cell.number_format = '#,##0.00'
        ws.cell(row=row_idx, column=6, value=e['reference_no'] or '')
        ws.cell(row=row_idx, column=7, value=e['description'] or '')

    col_widths = [12, 12, 35, 14, 14, 18, 35]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    fname = f"ekstre_{customer.name.replace(' ', '_')}_{today}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    wb.save(response)
    return response


@login_required
def payments(request):
    if request.user.is_staff:
        plans = PaymentPlan.objects.all().order_by('-created_at')
        cp_list = CustomerPayment.objects.all().order_by('-date', '-created_at')
    else:
        plans = PaymentPlan.objects.filter(user=request.user).order_by('-created_at')
        cp_list = CustomerPayment.objects.filter(user=request.user).order_by('-date', '-created_at')

    for plan in plans:
        plan.formatted_amount = fmt_tr(plan.amount)
    for cp in cp_list:
        cp.formatted_amount = fmt_tr(cp.amount)

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

def _parse_amount(text):
    """Türkçe veya standart biçimli tutar stringini Decimal'e çevirir."""
    t = text.strip().replace('₺', '').replace(' ', '')
    if ',' in t and '.' in t:
        t = t.replace('.', '').replace(',', '.')
    else:
        t = t.replace(',', '.')
    return Decimal(t or '0')


def _calc_installment(principal, n, monthly_rate_pct):
    """
    Taksit başı ödeme miktarını hesaplar.
    monthly_rate_pct: aylık faiz oranı (% cinsinden, ör. 2.5)
    Faizsiz → anapara / n
    Faizli  → annüite formülü: P × r(1+r)^n / ((1+r)^n - 1)
    """
    if monthly_rate_pct <= 0:
        return (principal / n).quantize(Decimal('0.01'))
    r = monthly_rate_pct / Decimal('100')
    factor = (1 + r) ** n
    return (principal * r * factor / (factor - 1)).quantize(Decimal('0.01'))


@login_required
def payment_create(request):
    errors = []
    form_data = {
        'customer':         request.POST.get('customer', ''),
        'plan_type':        request.POST.get('plan_type', ''),
        'payment_category': request.POST.get('payment_category', ''),
        'installments':     request.POST.get('installments', '12'),
        'total_amount':     request.POST.get('total_amount', ''),
        'interest_rate':    request.POST.get('interest_rate', '0'),
        'due_date':         request.POST.get('due_date', ''),
        'description':      request.POST.get('description', ''),
    }

    if request.method == 'POST':
        customer_id       = request.POST.get('customer')
        plan_type         = request.POST.get('plan_type')
        payment_category  = request.POST.get('payment_category')
        installments_text = request.POST.get('installments', '12')
        total_amount_text = request.POST.get('total_amount', '0')
        interest_rate_text= request.POST.get('interest_rate', '0').replace(',', '.')
        due_date          = request.POST.get('due_date') or None
        description       = request.POST.get('description', '')

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

        try:
            total_amount = _parse_amount(total_amount_text)
            if total_amount <= 0:
                errors.append('Toplam tutar sıfırdan büyük olmalıdır.')
        except (InvalidOperation, ValueError):
            errors.append('Geçerli bir toplam tutar girin.')
            total_amount = Decimal('0')

        try:
            interest_rate = Decimal(interest_rate_text or '0')
            if interest_rate < 0:
                errors.append('Faiz oranı negatif olamaz.')
        except (InvalidOperation, ValueError):
            errors.append('Geçerli bir faiz oranı girin.')
            interest_rate = Decimal('0')

        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                errors.append('Seçilen cari bulunamadı.')

        if customer and not request.user.is_staff and customer.user != request.user:
            return redirect('dashboard')

        if not errors and customer:
            from .models import Installment
            from dateutil.relativedelta import relativedelta

            installment_amount = _calc_installment(total_amount, installments, interest_rate)

            plan = PaymentPlan.objects.create(
                user=request.user,
                customer=customer,
                plan_type=plan_type,
                payment_category=payment_category,
                installments=installments,
                total_amount=total_amount,
                interest_rate=interest_rate,
                amount=installment_amount,
                due_date=due_date,
                description=description,
            )
            if due_date:
                start = dt_date.fromisoformat(str(due_date))
                for i in range(installments):
                    taksit_date = start + relativedelta(months=i) if plan_type == 'monthly' \
                                  else start + relativedelta(years=i)
                    Installment.objects.create(
                        plan=plan, number=i + 1,
                        due_date=taksit_date, amount=installment_amount,
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


@login_required
def installment_pay(request, pk):
    from .models import Installment
    inst = get_object_or_404(Installment, pk=pk)
    if not request.user.is_staff and inst.plan.user != request.user:
        raise Http404
    if request.method == 'POST':
        inst.is_paid    = True
        inst.paid_date  = request.POST.get('paid_date') or dt_date.today()
        inst.reference_no = request.POST.get('reference_no', '').strip()
        inst.note       = request.POST.get('note', '').strip()
        inst.save()
    return redirect('payments')


@login_required
def installment_unpay(request, pk):
    from .models import Installment
    inst = get_object_or_404(Installment, pk=pk)
    if not request.user.is_staff and inst.plan.user != request.user:
        raise Http404
    if request.method == 'POST':
        inst.is_paid   = False
        inst.paid_date = None
        inst.reference_no = ''
        inst.save()
    return redirect('payments')


@login_required
def recalculate_balance(request, pk):
    if request.user.is_staff:
        customer = get_object_or_404(Customer, pk=pk)
    else:
        customer = get_object_or_404(Customer, pk=pk, user=request.user)
    if request.method == 'POST':
        customer.recalculate_balance()
        messages.success(request, f"{customer.name} bakiyesi yeniden hesaplandı.")
    return redirect(f"/ekstre/?customer={pk}")
