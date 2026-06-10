from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.db.models import Sum, Count, Avg
from decimal import Decimal, InvalidOperation
from datetime import date as dt_date, timedelta
from transactions.models import Transaction
from customers.models import Customer
from .models import PaymentPlan, CustomerPayment, Expense, Installment
from .utils import fmt_tr

@login_required
def dashboard(request):
    from fields.models import FieldExpense
    user = request.user

    if user.is_staff:
        transactions    = Transaction.objects.all()
        cp_qs           = CustomerPayment.objects.all()
        exp_qs          = Expense.objects.all()
        fe_qs           = FieldExpense.objects.all()
        inst_qs         = Installment.objects.filter(is_paid=True)
    else:
        transactions    = Transaction.objects.filter(user=user)
        cp_qs           = CustomerPayment.objects.filter(user=user)
        exp_qs          = Expense.objects.filter(user=user)
        fe_qs           = FieldExpense.objects.filter(field__user=user)
        inst_qs         = Installment.objects.filter(is_paid=True, plan__user=user)

    total_sales     = transactions.filter(type='sale').aggregate(s=Sum('amount'))['s']     or Decimal('0')
    total_purchases = transactions.filter(type='purchase').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    profit          = total_sales - total_purchases

    tahsilat_alindi = cp_qs.filter(direction='alindi').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    tahsilat_odendi = cp_qs.filter(direction='odendi').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    inst_odenen     = inst_qs.aggregate(s=Sum('amount'))['s']                          or Decimal('0')
    gen_gider       = exp_qs.aggregate(s=Sum('amount'))['s']                           or Decimal('0')
    tarla_gider     = fe_qs.aggregate(s=Sum('amount'))['s']                            or Decimal('0')
    toplam_gider    = gen_gider + tarla_gider

    # Net kâr = satış − alış − giderler (brüt kârdan giderler düşülür)
    net_profit      = profit - toplam_gider

    # Açık alacak: satışlardan henüz tahsil edilmemiş tutar
    acik_alacak     = total_sales - tahsilat_alindi
    # Açık borç: alışlardan henüz ödenmeyen tutar
    acik_borc       = total_purchases - tahsilat_odendi - inst_odenen

    # Net Bakiye = açık alacak - açık borç - giderler
    # (satış → alacak+; tahsilat alındı → alacak−; alış → borç−; tahsilat ödendi → borç+)
    net_bakiye      = acik_alacak - acik_borc - toplam_gider

    recent_transactions = transactions.select_related('customer', 'field').order_by('-date', '-id')[:10]

    # — Son 6 ayın aylık trendi (grafik) —
    from django.db.models.functions import TruncMonth
    import json

    MONTHS_TR = {1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis', 5: 'May', 6: 'Haz',
                 7: 'Tem', 8: 'Ağu', 9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'}

    today = dt_date.today()
    month_start = today.replace(day=1)
    months = [month_start]
    for _ in range(5):
        months.insert(0, (months[0] - timedelta(days=1)).replace(day=1))
    chart_from = months[0]

    def _monthly_sums(qs):
        rows = qs.filter(date__gte=chart_from).annotate(m=TruncMonth('date')) \
                 .values('m').annotate(v=Sum('amount'))
        return {r['m'].strftime('%Y-%m'): r['v'] or Decimal('0') for r in rows if r['m']}

    m_sales = _monthly_sums(transactions.filter(type='sale'))
    m_purch = _monthly_sums(transactions.filter(type='purchase'))
    m_gexp  = _monthly_sums(exp_qs)
    m_fexp  = _monthly_sums(fe_qs)

    # Aylık satış miktarı (sadece kg birimli satışlar)
    kg_rows = transactions.filter(type='sale', unit='kg', date__gte=chart_from) \
                          .annotate(m=TruncMonth('date')).values('m').annotate(v=Sum('quantity'))
    m_kg = {r['m'].strftime('%Y-%m'): r['v'] or Decimal('0') for r in kg_rows if r['m']}

    chart_labels, chart_sales, chart_purch, chart_exp, chart_net, chart_kg = [], [], [], [], [], []
    for m in months:
        k = m.strftime('%Y-%m')
        s  = m_sales.get(k, Decimal('0'))
        p  = m_purch.get(k, Decimal('0'))
        ex = m_gexp.get(k, Decimal('0')) + m_fexp.get(k, Decimal('0'))
        chart_labels.append(f"{MONTHS_TR[m.month]} {m.year}")
        chart_sales.append(float(s))
        chart_purch.append(float(p))
        chart_exp.append(float(ex))
        chart_net.append(float(s - p - ex))
        chart_kg.append(float(m_kg.get(k, Decimal('0'))))

    has_chart_data = any(chart_sales) or any(chart_purch) or any(chart_exp)
    has_kg_data    = any(chart_kg)
    dashboard_chart = json.dumps({
        'labels': chart_labels, 'sales': chart_sales,
        'purchases': chart_purch, 'expenses': chart_exp, 'net': chart_net,
        'kg': chart_kg,
    })

    return render(request, 'dashboard/dashboard.html', {
        'total_sales':      total_sales,
        'total_purchases':  total_purchases,
        'profit':           profit,
        'net_profit':       net_profit,
        'tahsilat_alindi':  tahsilat_alindi,
        'tahsilat_odendi':  tahsilat_odendi,
        'inst_odenen':      inst_odenen,
        'gen_gider':        gen_gider,
        'tarla_gider':      tarla_gider,
        'toplam_gider':     toplam_gider,
        'acik_alacak':      acik_alacak,
        'acik_borc':        acik_borc,
        'net_bakiye':       net_bakiye,
        'greeting':         f"Merhaba {user.first_name or user.get_full_name() or user.username} 👋",
        'logged_user_name': user.username,
        'recent_transactions': recent_transactions,
        'dashboard_chart':  dashboard_chart,
        'has_chart_data':   has_chart_data,
        'has_kg_data':      has_kg_data,
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

            txn_qs = Transaction.objects.filter(customer=selected_customer).select_related('field').order_by('date', 'id')
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


# ─── Giderler ─────────────────────────────────────────────────────────────────

@login_required
def expense_list(request):
    from fields.models import Field
    from django.core.paginator import Paginator

    qs = Expense.objects.filter(user=request.user) if not request.user.is_staff \
         else Expense.objects.all()

    # — Filtreler —
    date_from  = request.GET.get('date_from', '').strip()
    date_to    = request.GET.get('date_to', '').strip()
    period     = request.GET.get('period', '').strip()
    cat_filter = request.GET.get('category', '').strip()

    today = dt_date.today()
    eff_from, eff_to = date_from, date_to

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
        elif period == 'son_30_gun':
            eff_from = (today - timedelta(days=30)).isoformat()
            eff_to   = today.isoformat()
        elif period == 'son_90_gun':
            eff_from = (today - timedelta(days=90)).isoformat()
            eff_to   = today.isoformat()

    if eff_from:
        qs = qs.filter(date__gte=eff_from)
    if eff_to:
        qs = qs.filter(date__lte=eff_to)
    if cat_filter:
        qs = qs.filter(category=cat_filter)

    total = qs.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    # Kategori özeti
    cat_summary = {}
    for row in qs.values('category').annotate(s=Sum('amount')).order_by('-s'):
        label = dict(Expense.CATEGORIES).get(row['category'], row['category'])
        cat_summary[label] = row['s']

    fields = Field.objects.filter(user=request.user) if not request.user.is_staff \
             else Field.objects.all()

    paginator   = Paginator(qs.select_related('field'), 50)
    expense_page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'dashboard/expenses.html', {
        'expenses':    expense_page,
        'page_obj':    expense_page,
        'total':       total,
        'cat_summary': cat_summary,
        'categories':  Expense.CATEGORIES,
        'fields':      fields,
        'filters': {
            'date_from':  date_from,
            'date_to':    date_to,
            'period':     period,
            'category':   cat_filter,
            'eff_from':   eff_from,
            'eff_to':     eff_to,
        },
        'fmt_total': fmt_tr(total),
    })


@login_required
def expense_create(request):
    if request.method != 'POST':
        return redirect('expense_list')

    from fields.models import Field

    date_str     = request.POST.get('date', '').strip()
    category     = request.POST.get('category', '').strip()
    description  = request.POST.get('description', '').strip()
    amount_text  = request.POST.get('amount', '').strip()
    reference_no = request.POST.get('reference_no', '').strip()
    field_id     = request.POST.get('field') or None

    try:
        exp_date = dt_date.fromisoformat(date_str) if date_str else dt_date.today()
    except ValueError:
        exp_date = dt_date.today()

    try:
        amount = _parse_amount(amount_text)
        if amount <= 0:
            messages.error(request, 'Tutar sıfırdan büyük olmalıdır.')
            return redirect('expense_list')
    except (InvalidOperation, ValueError):
        messages.error(request, 'Geçerli bir tutar girin.')
        return redirect('expense_list')

    field_obj = None
    if field_id:
        field_obj = Field.objects.filter(pk=field_id).first()

    Expense.objects.create(
        user=request.user,
        date=exp_date,
        category=category,
        description=description,
        amount=amount,
        reference_no=reference_no,
        field=field_obj,
    )
    messages.success(request, 'Gider kaydı eklendi.')
    return redirect('expense_list')


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if not request.user.is_staff and expense.user != request.user:
        raise Http404
    if request.method == 'POST':
        expense.delete()
    return redirect('expense_list')


# ─── Satış Miktarı Detayı ─────────────────────────────────────────────────────

@login_required
def sales_quantity(request):
    """Kg birimli satışların detay sayfası: toplam miktar, aylık grafik, cari kırılımı."""
    from django.db.models import Max
    from django.db.models.functions import TruncMonth
    import json

    user  = request.user
    tx_qs = Transaction.objects.all() if user.is_staff else Transaction.objects.filter(user=user)
    kg_qs = tx_qs.filter(type='sale', unit='kg')

    def fmt_kg(value):
        s = fmt_tr(value)
        return s[:-3] if s.endswith(',00') else s

    today        = dt_date.today()
    total_kg     = kg_qs.aggregate(s=Sum('quantity'))['s'] or Decimal('0')
    total_amount = kg_qs.aggregate(s=Sum('amount'))['s']   or Decimal('0')
    tx_count     = kg_qs.count()
    year_kg      = kg_qs.filter(date__gte=today.replace(month=1, day=1)) \
                        .aggregate(s=Sum('quantity'))['s'] or Decimal('0')
    month_kg     = kg_qs.filter(date__gte=today.replace(day=1)) \
                        .aggregate(s=Sum('quantity'))['s'] or Decimal('0')

    # — Tüm zamanların aylık satış miktarı —
    MONTHS_TR = {1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis', 5: 'May', 6: 'Haz',
                 7: 'Tem', 8: 'Ağu', 9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'}
    chart_labels, chart_kg = [], []
    monthly_rows = kg_qs.annotate(m=TruncMonth('date')).values('m') \
                        .annotate(kg=Sum('quantity')).order_by('m')
    for r in monthly_rows:
        if not r['m']:
            continue
        chart_labels.append(f"{MONTHS_TR[r['m'].month]} {r['m'].year}")
        chart_kg.append(float(r['kg'] or 0))

    # — Cari bazında kırılım —
    cust_rows = []
    rows = kg_qs.values('customer_id', 'customer__name') \
                .annotate(kg=Sum('quantity'), tutar=Sum('amount'),
                          cnt=Count('id'), last=Max('date')) \
                .order_by('-kg')
    for r in rows:
        kg    = r['kg']    or Decimal('0')
        tutar = r['tutar'] or Decimal('0')
        cust_rows.append({
            'customer_id': r['customer_id'],
            'name':        r['customer__name'],
            'kg':          fmt_kg(kg),
            'pct':         float(kg / total_kg * 100) if total_kg > 0 else 0,
            'cnt':         r['cnt'],
            'tutar':       fmt_tr(tutar),
            'avg_price':   fmt_tr(tutar / kg) if kg > 0 else '—',
            'last':        r['last'],
        })

    return render(request, 'dashboard/sales_quantity.html', {
        'total_kg':     fmt_kg(total_kg),
        'year_kg':      fmt_kg(year_kg),
        'month_kg':     fmt_kg(month_kg),
        'total_amount': fmt_tr(total_amount),
        'tx_count':     tx_count,
        'cust_rows':    cust_rows,
        'chart_json':   json.dumps({'labels': chart_labels, 'kg': chart_kg}),
        'has_data':     tx_count > 0,
    })


# ─── Karlılık Tablosu ─────────────────────────────────────────────────────────

@login_required
def profitability(request):
    from fields.models import Field, FieldExpense
    from transactions.models import Product as TxProduct
    from django.db.models.functions import TruncMonth
    import json

    user = request.user

    # — Filtreler —
    date_from = request.GET.get('date_from', '').strip()
    date_to   = request.GET.get('date_to', '').strip()
    period    = request.GET.get('period', '').strip()

    today = dt_date.today()
    eff_from, eff_to = date_from, date_to

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
            eff_from = today.replace(year=today.year - 1, month=1,  day=1).isoformat()
            eff_to   = today.replace(year=today.year - 1, month=12, day=31).isoformat()
        elif period == 'son_30_gun':
            eff_from = (today - timedelta(days=30)).isoformat()
            eff_to   = today.isoformat()
        elif period == 'son_90_gun':
            eff_from = (today - timedelta(days=90)).isoformat()
            eff_to   = today.isoformat()

    # — Temel sorgu setleri —
    tx_qs  = Transaction.objects.all()  if user.is_staff else Transaction.objects.filter(user=user)
    exp_qs = Expense.objects.all()      if user.is_staff else Expense.objects.filter(user=user)
    fe_qs  = FieldExpense.objects.all() if user.is_staff else FieldExpense.objects.filter(field__user=user)

    if eff_from:
        tx_qs  = tx_qs.filter(date__gte=eff_from)
        exp_qs = exp_qs.filter(date__gte=eff_from)
        fe_qs  = fe_qs.filter(date__gte=eff_from)
    if eff_to:
        tx_qs  = tx_qs.filter(date__lte=eff_to)
        exp_qs = exp_qs.filter(date__lte=eff_to)
        fe_qs  = fe_qs.filter(date__lte=eff_to)

    # — Genel Özet —
    total_sales     = tx_qs.filter(type='sale').aggregate(s=Sum('amount'))['s']     or Decimal('0')
    total_purchases = tx_qs.filter(type='purchase').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    total_gen_exp   = exp_qs.aggregate(s=Sum('amount'))['s']                         or Decimal('0')
    total_field_exp = fe_qs.aggregate(s=Sum('amount'))['s']                          or Decimal('0')
    total_expenses  = total_gen_exp + total_field_exp
    gross_profit    = total_sales - total_purchases
    net_profit      = gross_profit - total_expenses
    gross_margin    = (gross_profit / total_sales * 100).quantize(Decimal('0.1')) if total_sales > 0 else Decimal('0')
    net_margin      = (net_profit  / total_sales * 100).quantize(Decimal('0.1')) if total_sales > 0 else Decimal('0')

    # Ürün bazlı satış dağılımı
    slug_to_name = {p.slug: p.name for p in TxProduct.objects.all()}
    product_rows = []
    for row in tx_qs.filter(type='sale').values('product').annotate(
            total=Sum('amount'), qty=Sum('quantity')).order_by('-total')[:10]:
        product_rows.append({
            'name':  slug_to_name.get(row['product'], row['product']),
            'total': row['total'],
            'qty':   row['qty'],
            'pct':   float(row['total'] / total_sales * 100) if total_sales > 0 else 0,
        })

    # — Cari Bazlı —
    from customers.models import Customer
    cust_sales_map = {
        r['customer_id']: r
        for r in tx_qs.filter(type='sale').values('customer_id').annotate(
            sales=Sum('amount'), sale_count=Count('id'))
    }
    cust_purch_map = {
        r['customer_id']: r
        for r in tx_qs.filter(type='purchase').values('customer_id').annotate(
            purch=Sum('amount'), purch_count=Count('id'))
    }
    all_cust_ids = set(cust_sales_map) | set(cust_purch_map)
    customers_qs = Customer.objects.filter(pk__in=all_cust_ids).only('id', 'name', 'phone', 'customer_type')
    cust_rows = []
    for c in customers_qs:
        cs = cust_sales_map.get(c.pk, {})
        cp = cust_purch_map.get(c.pk, {})
        sales      = cs.get('sales')   or Decimal('0')
        purchases  = cp.get('purch')   or Decimal('0')
        sale_cnt   = cs.get('sale_count', 0)
        purch_cnt  = cp.get('purch_count', 0)
        gross      = sales - purchases
        margin     = (gross / sales * 100).quantize(Decimal('0.1')) if sales > 0 else Decimal('0')
        cust_rows.append({
            'customer':  c,
            'sales':     sales,
            'purchases': purchases,
            'gross':     gross,
            'margin':    margin,
            'tx_count':  sale_cnt + purch_cnt,
        })
    cust_rows.sort(key=lambda r: r['gross'], reverse=True)

    # — Ürün Bazlı —
    prod_sales_map = {
        r['product']: r
        for r in tx_qs.filter(type='sale').values('product').annotate(
            sales=Sum('amount'), qty=Sum('quantity'),
            avg_price=Avg('unit_price'), count=Count('id'))
    }
    prod_purch_map = {
        r['product']: r
        for r in tx_qs.filter(type='purchase').values('product').annotate(
            purch=Sum('amount'), qty=Sum('quantity'),
            avg_price=Avg('unit_price'), count=Count('id'))
    }
    all_prod_slugs = set(prod_sales_map) | set(prod_purch_map)
    prod_rows = []
    for slug in all_prod_slugs:
        ps = prod_sales_map.get(slug, {})
        pp = prod_purch_map.get(slug, {})
        p_sales  = ps.get('sales')     or Decimal('0')
        p_purch  = pp.get('purch')     or Decimal('0')
        p_qty_s  = ps.get('qty')       or Decimal('0')
        p_qty_p  = pp.get('qty')       or Decimal('0')
        p_avg_s  = ps.get('avg_price') or Decimal('0')
        p_avg_p  = pp.get('avg_price') or Decimal('0')
        p_cnt_s  = ps.get('count', 0)
        p_cnt_p  = pp.get('count', 0)
        p_gross  = p_sales - p_purch
        p_margin = (p_gross / p_sales * 100).quantize(Decimal('0.1')) if p_sales > 0 else Decimal('0')
        p_pct    = float(p_sales / total_sales * 100) if total_sales > 0 else 0
        prod_rows.append({
            'slug':      slug,
            'name':      slug_to_name.get(slug, slug),
            'sales':     p_sales,
            'purchases': p_purch,
            'qty_sale':  p_qty_s,
            'qty_purch': p_qty_p,
            'avg_sale':  p_avg_s.quantize(Decimal('0.01')) if p_avg_s else Decimal('0'),
            'avg_purch': p_avg_p.quantize(Decimal('0.01')) if p_avg_p else Decimal('0'),
            'cnt_sale':  p_cnt_s,
            'cnt_purch': p_cnt_p,
            'gross':     p_gross,
            'margin':    p_margin,
            'pct':       round(p_pct, 1),
        })
    prod_rows.sort(key=lambda r: r['sales'], reverse=True)

    # — Tarla Bazlı —
    fields = Field.objects.all() if user.is_staff else Field.objects.filter(user=user)
    field_rows = []
    for f in fields:
        fs  = tx_qs.filter(field=f, type='sale').aggregate(s=Sum('amount'))['s']     or Decimal('0')
        fp  = tx_qs.filter(field=f, type='purchase').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        ffe = fe_qs.filter(field=f).aggregate(s=Sum('amount'))['s']                   or Decimal('0')
        fge = exp_qs.filter(field=f).aggregate(s=Sum('amount'))['s']                  or Decimal('0')
        fe_total = ffe + fge
        fg   = fs - fp
        fn   = fg - fe_total
        field_rows.append({'field': f, 'sales': fs, 'purchases': fp,
                           'expenses': fe_total, 'gross': fg, 'net': fn})

    ua_sales = tx_qs.filter(field__isnull=True, type='sale').aggregate(s=Sum('amount'))['s']     or Decimal('0')
    ua_purch = tx_qs.filter(field__isnull=True, type='purchase').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    ua_exp   = exp_qs.filter(field__isnull=True).aggregate(s=Sum('amount'))['s']                  or Decimal('0')
    ua_gross = ua_sales - ua_purch
    ua_net   = ua_gross - ua_exp

    # — Dönem Bazlı (Aylık) —
    MONTHS_TR = {1:'Oca',2:'Şub',3:'Mar',4:'Nis',5:'May',6:'Haz',
                 7:'Tem',8:'Ağu',9:'Eyl',10:'Eki',11:'Kas',12:'Ara'}

    monthly = {}

    def _add(rows, key):
        for row in rows:
            m = row.get('m')
            if not m:
                continue
            k = m.strftime('%Y-%m')
            if k not in monthly:
                monthly[k] = {
                    'label': f"{MONTHS_TR[m.month]} {m.year}",
                    'sales': Decimal('0'), 'purchases': Decimal('0'),
                    'gen_expenses': Decimal('0'), 'field_expenses': Decimal('0'),
                }
            monthly[k][key] += row['v'] or Decimal('0')

    _add(tx_qs.filter(type='sale').annotate(m=TruncMonth('date')).values('m').annotate(v=Sum('amount')), 'sales')
    _add(tx_qs.filter(type='purchase').annotate(m=TruncMonth('date')).values('m').annotate(v=Sum('amount')), 'purchases')
    _add(exp_qs.annotate(m=TruncMonth('date')).values('m').annotate(v=Sum('amount')), 'gen_expenses')
    _add(fe_qs.annotate(m=TruncMonth('date')).values('m').annotate(v=Sum('amount')), 'field_expenses')

    monthly_list = []
    for k in sorted(monthly.keys()):
        d = monthly[k].copy()
        d['expenses'] = d['gen_expenses'] + d['field_expenses']
        d['gross']    = d['sales'] - d['purchases']
        d['net']      = d['gross'] - d['expenses']
        monthly_list.append(d)

    chart_json = json.dumps({
        'labels':   [m['label']          for m in monthly_list],
        'sales':    [float(m['sales'])    for m in monthly_list],
        'purchases':[float(m['purchases'])for m in monthly_list],
        'expenses': [float(m['expenses']) for m in monthly_list],
        'net':      [float(m['net'])      for m in monthly_list],
    })

    return render(request, 'dashboard/profitability.html', {
        'filters': {'date_from': date_from, 'date_to': date_to,
                    'period': period, 'eff_from': eff_from, 'eff_to': eff_to},
        'total_sales':     total_sales,
        'total_purchases': total_purchases,
        'total_gen_exp':   total_gen_exp,
        'total_field_exp': total_field_exp,
        'total_expenses':  total_expenses,
        'gross_profit':    gross_profit,
        'net_profit':      net_profit,
        'gross_margin':    gross_margin,
        'net_margin':      net_margin,
        'product_rows':    product_rows,
        'cust_rows':       cust_rows,
        'prod_rows':       prod_rows,
        'field_rows':      field_rows,
        'ua_sales':        ua_sales,
        'ua_purch':        ua_purch,
        'ua_exp':          ua_exp,
        'ua_gross':        ua_gross,
        'ua_net':          ua_net,
        'has_unassigned':  any([ua_sales, ua_purch, ua_exp]),
        'monthly_list':    monthly_list,
        'chart_json':      chart_json,
    })
