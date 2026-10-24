from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django_svg_image_form_field import SvgAndImageFormField
from django.core.exceptions import ValidationError

from .models import *

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'
        field_classes = {'icon': SvgAndImageFormField}


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=40)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Имя пользователя', 'first_name': 'Ваше имя',
            'last_name': 'Ваша фамилия', 'email': 'Ваша почта',
            'password1': 'Пароль', 'password2': 'Повторите пароль',
            'phone_number': 'Номер телефона',
        }
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': placeholders[name]})

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Такая почта уже зарегистрирована.')
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Имя пользователя'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Пароль'})


class CheckoutForm(forms.ModelForm):
    # In the model these are optional for compatibility with old orders,
    # but they are required during new checkout.
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)

    class Meta:
        model = Delivery
        fields = ('region', 'city', 'street', 'home', 'flat', 'phone',
                  'comment', 'first_name', 'last_name', 'email')
        widgets = {
            'region': forms.Select(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Улица'}),
            'home': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Дом'}),
            'flat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Квартира (необязательно)'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон получателя'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Комментарий к заказу', 'rows': 3}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ваше имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ваша фамилия'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Электронная почта'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['region'].empty_label = 'Выберите регион'
        self.fields['city'].empty_label = 'Выберите город'
        self.fields['city'].queryset = City.objects.none()
        region_id = self.data.get('region') if self.is_bound else self.initial.get('region')
        if region_id and str(region_id).isdigit():
            self.fields['city'].queryset = City.objects.filter(region_id=region_id)

    def clean(self):
        data = super().clean()
        if data.get('city') and data.get('region'):
            if data['city'].region_id != data['region'].pk:
                self.add_error('city', 'Город не относится к выбранному региону.')
        return data


class ImagesProductInlineForm(forms.ModelForm):
    class Meta:
        model = ImagesProduct
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get('product') or self.instance.product_id
        color = cleaned_data.get('color')

        product_id = getattr(product, 'pk', product)

        if color and product_id and color.product_id != product_id:
            raise ValidationError(
                'Выбранный цвет принадлежит другому товару.'
            )

        return cleaned_data

class ProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=40)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
