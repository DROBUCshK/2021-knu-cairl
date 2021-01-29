# -*- coding: utf-8 -*-
"""house_prices.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ERlcU8-oa7aTFZrwDbbKdkkfVGQkDHyz

**Importing all libraries**
"""

import warnings
import numpy as np
import pandas as pd
import seaborn as sns
import xgboost as xgb
import scipy.stats as stats
import statsmodels.api as sm
import matplotlib.pyplot as plt
from scipy.stats import skew, norm
from sklearn.neighbors import KNeighborsRegressor
from google.colab import files
from sklearn.svm import SVR
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeRegressor
from mlxtend.regressor import StackingRegressor
from sklearn.linear_model import LinearRegression, BayesianRidge
from sklearn.model_selection import KFold, cross_val_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error
pd.options.mode.chained_assignment = None
# %matplotlib inline
warnings.filterwarnings('ignore')

"""**Loading the data**"""

files.upload()

train_data = pd.read_csv("train.csv")
test_data = pd.read_csv("test.csv")

"""**Exploratory data analysis (EDA) and Visualization**"""

print(test_data.info())
print(test_data.isna().sum())

"""**Let's explore our target variable and how the other features influence it.**"""

pip install flake8 pycodestyle_magic

# Commented out IPython magic to ensure Python compatibility.
# %load_ext pycodestyle_magic

(mu, sigma) = norm.fit(train_data['SalePrice'])

plt.figure(figsize=(12, 6))
sns.distplot(train_data['SalePrice'], kde=True, hist=True, fit=norm)
plt.title('SalePrice distribution vs Normal Distribution', fontsize=13)
plt.xlabel("House's sale Price in $", fontsize=12)
plt.legend([r'Normal dist. ($\mu=$ {:.2f} and $\sigma=$ {:.2f} )'.format(mu, sigma)], loc='best')
plt.show()

"""**The distribution does not seem to be normal, but highly right-skewed.**"""

print("Skewness: %f" % abs(train_data['SalePrice']).skew())
print("Kurtosis: %f" % abs(train_data['SalePrice']).kurt())

"""**Correlation matrix**

Let's see which are the feature that correlate most with our target variable.
"""

f, ax = plt.subplots(figsize=(30, 25))
mat = train_data.corr('pearson')
mask = np.triu(np.ones_like(mat, dtype=bool))
cmap = sns.diverging_palette(230, 20, as_cmap=True)
sns.heatmap(mat, mask=mask, cmap=cmap, vmax=1, center=0, annot=True,
            square=True, linewidths=.5, cbar_kws={"shrink": .5})
plt.show()

"""So we can see that **OverallQual, TotRmsAbvGrd, GrLivArea, TotalBsmtSF, YearBuilt, YrSold** features correlate most with our target variable.

**DATA PREPROCESSING**

Test dataset contains some observations not present in the training dataset.

The use of dummy coding could raise several issues, so let's concatenate 

Train and Test sets, preprocess, and divide them again.
"""

target = train_data['SalePrice']
test_id = test_data['Id']
test = test_data.drop(['Id'], axis=1)
train = train_data.drop(['SalePrice', 'Id'], axis=1)
train_test = pd.concat([train, test], axis=0, sort=False)

"""Let's check the amount of missed(Nan) values for each variable"""

missed = pd.DataFrame(train_test.isna().sum(), columns=['Amount'])
missed['feat'] = missed.index
missed['Perc(%)'] = (missed['Amount'] / 1460) * 100
missed = missed[missed['Amount'] > 0]
missed = missed.sort_values(by=['Amount'])
missed

"""Plotting missed(Nan)"""

plt.figure(figsize=(15, 5))
sns.barplot(x=missed['feat'], y=missed['Perc(%)'])
plt.xticks(rotation=45)
plt.title('Features containing Nan')
plt.xlabel('Features')
plt.ylabel('% of Missing Data')
plt.show()

"""Filling Categorical NaN"""

for col in ('BsmtQual', 'BsmtCond', 'BsmtExposure', 'BsmtFinType1', 'BsmtFinType2'):
    train_test[col] = train_test[col].fillna('None')

for col in ['GarageType', 'GarageFinish', 'GarageQual', 'GarageCond']:
    train_test[col] = train_test[col].fillna('None')

for col in ('GarageArea', 'GarageCars'):
    train_test[col] = train_test[col].fillna(0)

train_test["PoolQC"] = train_test["PoolQC"].fillna("None")
train_test["Alley"] = train_test["Alley"].fillna("None")
train_test['FireplaceQu'] = train_test['FireplaceQu'].fillna("None")
train_test['Fence'] = train_test['Fence'].fillna("None")
train_test['MiscFeature'] = train_test['MiscFeature'].fillna("None")
train_test['Functional'] = train_test['Functional'].fillna('Typ')
train_test['Electrical'] = train_test['Electrical'].fillna("SBrkr")
train_test['KitchenQual'] = train_test['KitchenQual'].fillna("TA")
train_test['Exterior1st'] = train_test['Exterior1st'].fillna(train_test['Exterior1st'].mode()[0])
train_test['Exterior2nd'] = train_test['Exterior2nd'].fillna(train_test['Exterior2nd'].mode()[0])
train_test['SaleType'] = train_test['SaleType'].fillna(train_test['SaleType'].mode()[0])

"""Converting non-numeric predictors stored as numbers into string"""

train_test['MSSubClass'] = train_test['MSSubClass'].apply(str)
train_test['YrSold'] = train_test['YrSold'].apply(str)
train_test['MoSold'] = train_test['MoSold'].apply(str)

"""Removing the useless variables"""

useless = ['GarageYrBlt', 'YearRemodAdd'] 
train_test = train_test.drop(useless, axis=1)

# Imputing with KnnRegressor 


def impute_knn(df):
    ttn = train_test.select_dtypes(include=[np.number])
    ttc = train_test.select_dtypes(exclude=[np.number])

    cols_nan = ttn.columns[ttn.isna().any()].tolist()   
    cols_no_nan = ttn.columns.difference(cols_nan).values

    for col in cols_nan:
        imp_test = ttn[ttn[col].isna()]
        imp_train = ttn.dropna()    
        model = KNeighborsRegressor(n_neighbors=5)
        knr = model.fit(imp_train[cols_no_nan], imp_train[col])
        ttn.loc[ttn[col].isna(), col] = knr.predict(imp_test[cols_no_nan])

    return pd.concat([ttn, ttc], axis=1)


train_test = impute_knn(train_test)

objects = []
for i in train_test.columns:
    if train_test[i].dtype == object:
        objects.append(i)
train_test.update(train_test[objects].fillna('None'))

"""**FEATURE ENGINEERING**"""

train_test["SqFtPerRoom"] = (train_test["GrLivArea"] / (train_test[
    "TotRmsAbvGrd"] + train_test["FullBath"] + train_test[
        "HalfBath"] + train_test["KitchenAbvGr"]))

train_test['Total_Home_Quality'] = (train_test[
    'OverallQual'] + train_test['OverallCond'])

train_test['Total_Bathrooms'] = (train_test[
    'FullBath'] + (0.5 * train_test['HalfBath']) + train_test[
        'BsmtFullBath'] + (0.5 * train_test['BsmtHalfBath']))

train_test["HighQualSF"] = train_test["1stFlrSF"] + train_test["2ndFlrSF"]

# Creating dummy variables from categorical features

train_test_dummy = pd.get_dummies(train_test)

# Fetch all numeric features

numeric_features = train_test_dummy.dtypes[
    train_test_dummy.dtypes != object].index
skewed_features = train_test_dummy[numeric_features].apply(
    lambda x: skew(x)).sort_values(ascending=False)
high_skew = skewed_features[skewed_features > 0.5]
skew_index = high_skew.index

# Normalize skewed features using log_transformation

for i in skew_index:
    train_test_dummy[i] = np.log1p(train_test_dummy[i])

"""Let's use a log transformation in order to tranform our target distribution into a normal one"""

# SalePrice before transformation

fig, ax = plt.subplots(1, 2, figsize=(15, 5))
fig.suptitle(" qq-plot & distribution SalePrice ", fontsize=15)

sm.qqplot(target, stats.t, distargs=(4,), fit=True, line="45", ax=ax[0])

sns.distplot(target, kde=True, hist=True, fit=norm, ax=ax[1])
plt.show()

# SalePrice after transformation

target_log = np.log1p(target)

fig, ax = plt.subplots(1, 2, figsize=(15, 5))
fig.suptitle("qq-plot & distribution SalePrice ", fontsize=15)

sm.qqplot(target_log, stats.t, distargs=(4,), fit=True, line="45", ax=ax[0])
sns.distplot(target_log, kde=True, hist=True, fit=norm, ax=ax[1])
plt.show()

"""**Modeling**"""

# Train-Test separation

train = train_test_dummy[0:1460]
test = train_test_dummy[1460:]
test['Id'] = test_id

# Creation of the RMSE metric:


def rmse(y, y_pred):
    return np.sqrt(mean_squared_error(y, y_pred))


def cv_rmse(model):
    rmse = np.sqrt(-cross_val_score(model, train, target_log, scoring="neg_mean_squared_error", cv=kf))
    return (rmse)


# 10 Fold Cross validation

kf = KFold(n_splits=10, random_state=42, shuffle=True)

cv_scores = []
cv_std = []

baseline_models = ['Linear_Reg.', 'Bayesian_Ridge_Reg.', 'LGBM_Reg.', 'SVR',
                   'Dec_Tree_Reg.', 'Random_Forest_Reg.', 'XGB_Reg.',
                   'Grad_Boost_Reg.', 'Cat_Boost_Reg.', 'Stacked_Reg.']

# Linear Regression

lreg = LinearRegression()
score_lreg = cv_rmse(lreg)
cv_scores.append(score_lreg.mean())
cv_std.append(score_lreg.std())

# Bayesian Ridge Regression

brr = BayesianRidge(compute_score=True)
score_brr = cv_rmse(brr)
cv_scores.append(score_brr.mean())
cv_std.append(score_brr.std())

# Light Gradient Boost Regressor

l_gbm = LGBMRegressor(objective='regression')
score_l_gbm = cv_rmse(l_gbm)
cv_scores.append(score_l_gbm.mean())
cv_std.append(score_l_gbm.std())

# Support Vector Regression

svr = SVR()
score_svr = cv_rmse(svr)
cv_scores.append(score_svr.mean())
cv_std.append(score_svr.std())

# Decision Tree Regressor

dtr = DecisionTreeRegressor()
score_dtr = cv_rmse(dtr)
cv_scores.append(score_dtr.mean())
cv_std.append(score_dtr.std())

# Random Forest Regressor

rfr = RandomForestRegressor()
score_rfr = cv_rmse(rfr)
cv_scores.append(score_rfr.mean())
cv_std.append(score_rfr.std())

# XGB Regressor

xgb = xgb.XGBRegressor()
score_xgb = cv_rmse(xgb)
cv_scores.append(score_xgb.mean())
cv_std.append(score_xgb.std())

# Gradient Boost Regressor

gbr = GradientBoostingRegressor()
score_gbr = cv_rmse(gbr)
cv_scores.append(score_gbr.mean())
cv_std.append(score_gbr.std())

# Cat Boost Regressor

catb = CatBoostRegressor()
score_catb = cv_rmse(catb)
cv_scores.append(score_catb.mean())
cv_std.append(score_catb.std())

# Stacked Regressor

stack_gen = StackingRegressor(regressors=(CatBoostRegressor(),
                                          LinearRegression(),
                                          BayesianRidge(),
                                          GradientBoostingRegressor()),
                              meta_regressor=CatBoostRegressor(),
                              use_features_in_secondary=True)

score_stack_gen = cv_rmse(stack_gen)
cv_scores.append(score_stack_gen.mean())
cv_std.append(score_stack_gen.std())

final_cv_score = pd.DataFrame(baseline_models, columns=['Regressors'])
final_cv_score['RMSE_mean'] = cv_scores
final_cv_score['RMSE_std'] = cv_std

final_cv_score

plt.figure(figsize=(12, 8))
sns.barplot(final_cv_score['Regressors'], final_cv_score['RMSE_mean'])
plt.xlabel('Regressors', fontsize=12)
plt.ylabel('CV_Mean_RMSE', fontsize=12)
plt.xticks(rotation=45)
plt.show()

"""As we can see Cat Boost Reg has the smallest Mean RMSE.

So we will use it for predicting results
"""

X_train, X_val, y_train, y_val = train_test_split(train, target_log, test_size=0.1, random_state=42)

# Cat Boost Regressor

params = {'iterations': 6000,
          'learning_rate': 0.005,
          'depth': 4,
          'l2_leaf_reg': 1,
          'eval_metric': 'RMSE',
          'early_stopping_rounds': 200,
          'verbose': 200,
          'random_seed': 42}

cat = CatBoostRegressor(**params)
cat_model = cat_f.fit(X_train, y_train,
                      eval_set=(X_val, y_val),
                      plot=True,
                      verbose=False)

cat_pred = cat_model_f.predict(X_val)
cat_score = rmse(y_val, catf_pred)

cat_score

"""**Submission**"""

pred = cat_f.predict(test)
output = pd.DataFrame(test_id, columns=['Id'])
output['SalePrice'] = np.expm1(pred)
output.to_csv("submission.csv", index=False, header=True)