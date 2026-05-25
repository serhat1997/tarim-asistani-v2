from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import reverse
from .models import Customer


@login_required
def customer_list(request):
    if request.user.is_staff:
        customers = Customer.objects.all().order_by('name')
    else:
        customers = Customer.objects.filter(user=request.user).order_by('name')

    selected_customer = None
    customer_id = request.GET.get('customer')
    if customer_id:
        try:
            if request.user.is_staff:
                selected_customer = Customer.objects.get(id=customer_id)
            else:
                selected_customer = Customer.objects.get(id=customer_id, user=request.user)
        except Customer.DoesNotExist:
            pass

    return render(request, 'customers/customer_list.html', {
        'customers': customers,
        'selected_customer': selected_customer,
    })


@login_required
def customer_create(request):
    errors = []
    form_data = {
        'name': '', 'tc_vkn': '', 'phone': '', 'email': '', 'address': '',
    }

    if request.method == 'POST':
        form_data = {
            'name':    request.POST.get('name', '').strip(),
            'tc_vkn':  request.POST.get('tc_vkn', '').strip(),
            'phone':   request.POST.get('phone', '').strip(),
            'email':   request.POST.get('email', '').strip(),
            'address': request.POST.get('address', '').strip(),
        }
        if not form_data['name']:
            errors.append('Ad Soyad / Firma Adı zorunludur.')

        if not errors:
            Customer.objects.create(user=request.user, **form_data)
            return redirect('customer_list')

    return render(request, 'customers/customer_form.html', {
        'form_data': form_data,
        'errors': errors,
        'action': 'create',
    })


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if not request.user.is_staff and customer.user != request.user:
        raise Http404

    errors = []
    form_data = {
        'name':    customer.name,
        'tc_vkn':  customer.tc_vkn,
        'phone':   customer.phone,
        'email':   customer.email,
        'address': customer.address,
    }

    if request.method == 'POST':
        form_data = {
            'name':    request.POST.get('name', '').strip(),
            'tc_vkn':  request.POST.get('tc_vkn', '').strip(),
            'phone':   request.POST.get('phone', '').strip(),
            'email':   request.POST.get('email', '').strip(),
            'address': request.POST.get('address', '').strip(),
        }
        if not form_data['name']:
            errors.append('Ad Soyad / Firma Adı zorunludur.')

        if not errors:
            for field, value in form_data.items():
                setattr(customer, field, value)
            customer.save()
            return redirect(reverse('customer_list') + f'?customer={customer.pk}')

    return render(request, 'customers/customer_form.html', {
        'form_data': form_data,
        'errors': errors,
        'action': 'edit',
        'customer': customer,
    })


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if not request.user.is_staff and customer.user != request.user:
        raise Http404
    if request.method == 'POST':
        customer.delete()
        return redirect('customer_list')
    return redirect(reverse('customer_list') + f'?customer={pk}')


@login_required
def customer_detail(request, pk):
    return redirect(reverse('customer_list') + f'?customer={pk}')
