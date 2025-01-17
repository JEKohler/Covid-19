""" Data Utility Module with helping functions used from different
classes (Oxford and Mobility).
"""
import pandas as pd

from world_data import WorldPopulationData


class COL:
	# oxford data columns
	c1 = 'C1_School_closing'
	c2 = 'C2_Workplace_closing'
	c3 = 'C3_Cancel_public_events'
	c4 = 'C4_Restrictions_on_gatherings'
	c5 = 'C5_Close_public_transport'
	c6 = 'C6_Stay_at_home_requirements'
	c7 = 'C7_Restrictions_on_internal_movement'
	c8 = 'C8_International_travel_controls'
	
	e1 = 'E1_Income_support'
	e2 = 'E2_Debt/contract_relief'
	e3 = 'E3_Fiscal_measures'
	e4 = 'E4_International_support'
	
	h1 = 'H1_Public_information_campaigns'
	h2 = 'H2_Testing_policy'
	h3 = 'H3_Contact_tracing'
	h4 = 'H4_Emergency_investment_in_healthcare'
	h5 = 'H5_Investment_in_vaccines'
	
	cc = 'ConfirmedCases'
	cd = 'ConfirmedDeaths'
	rc = 'Recovered'
	ac = 'Active'
	
	dcc = 'DailyConfirmedCases'
	dcd = 'DailyConfirmedDeaths'
	drc = 'DailyRecovered'
	dac = 'DailyActive'
	
	si = 'StringencyIndex'
	
	# stringency features
	ci_cols = [h1, c1, c2, c3, c4, c5, c6, c7, c8]
	# translated features
	si_cols = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9']


class FEATURE:
	stringency = 'st'
	stringency_sum = 'St'
	mobility = 'mt'
	mobility_sum = 'Mt'
	public_information = 'S1'
	school_closing = 'S2'
	workplace_closing = 'S3'
	cancel_public_events = 'S4'
	restrictions_on_gatherings = 'S5'
	close_public_transport = 'S6'
	stay_at_home_requirements = 'S7'
	restrictions_on_internal_movement = 'S8'
	international_travel_controls = 'S9'


FEATURE_DICT = {FEATURE.stringency: 'Stringency (st)',
                FEATURE.stringency_sum: 'Stringeny, sum (St)',
                FEATURE.mobility: 'Mobility (mt)',
                FEATURE.public_information: 'Public Information Campaigns (s1)',
                FEATURE.school_closing: 'School Closing (s2)',
                FEATURE.workplace_closing: 'Workplace Closing (s3)',
                FEATURE.cancel_public_events: 'Cancel Public Events (s4)',
                FEATURE.restrictions_on_gatherings: 'Restriction on Gatherings (s5)',
                FEATURE.close_public_transport: 'Close Public Transport (s6)',
                FEATURE.stay_at_home_requirements: 'Stay At Home Requirements (s7)',
                FEATURE.restrictions_on_internal_movement: 'Restriction on Internal Movement (s8)',
                FEATURE.international_travel_controls: 'International Travel Controls (s9)'}


OXFORD_DATA_URL = "https://raw.githubusercontent.com/OxCGRT/covid-policy-tracker/master/data/OxCGRT_latest.csv"


def load_oxford_data() -> pd.DataFrame:
	"""Load Oxford Covid-19 Government Response Tracker (OxCGRT) data
	from repository, reformat date and rename some columns.
	
	Returns
	-------
	df: DataFrame
		Modified data of OxCGRT data
	"""
	print("Load latest Oxford data from URL...")
	try:
		df = pd.read_csv(OXFORD_DATA_URL)
		# reformat date
		df["DateTime"] = pd.to_datetime(df["Date"], format="%Y%m%d", errors="ignore")
		df["Date"] = df["DateTime"].dt.strftime("%Y-%m-%d")
		
		# rename and clean columns
		new_cols = ['_'.join(c.split(' ')) for c in df.columns]
		for o, n in zip(df.columns, new_cols):
			df.rename({o: n}, axis=1, inplace=True)
		
		df = df.drop(columns=['ConfirmedCases', 'ConfirmedDeaths'])
		df = df.rename(columns={'CountryCode': 'Country_Code'})
		
		print(" - loaded:", df.shape)
		
		return df
	
	except Exception as e:
		print("ERROR: No data available for URL", OXFORD_DATA_URL)
		print(e)


def process_data(df, old_df) -> pd.DataFrame:
	"""Helper Function that performs some processing steps.

	Parameters
	----------
	df: DataFrame
		Data to process and finally returned
	old_df: DataFrame
		Initial data without any processing steps applied
	
	Returns
	-------
	df: DataFrame
		Processed data
	"""
	print("Process data...")
	df = extend_data(df, old_df)
	df = fill_missing_values(df)
	df = add_world_population_data(df)
	df = create_features(df)
	
	return df


def extend_data(df, old_df) -> pd.DataFrame:
	"""Extend data does different things:
	* transform Oxford indices into continuous values
	* fill with NaN
	* extend date to current date for all countries
	* fill missing values with last known notNaN (Oxford doesn't
	  completely continues time series, if there are no values)
	
	Parameters
	----------
	df: DataFrame
		Data to process and finally returned
	old_df: DataFrame
		Initial data without any processing steps applied
	
	Returns
	-------
	df: DataFrame
		Extended data
	"""
	i = 0
	for s_col in COL.ci_cols:
		print("- process col", s_col)
		if i == 8:  # C_8
			transform_to_mobility(df, old_df, s_col, has_flag=False)
		else:
			transform_to_mobility(df, old_df, s_col)
		i += 1
		
	# fill all NaN with zero
	for col in df.columns:
		df[col].fillna(0, inplace=True)
		
	# sort values
	df = df.sort_values(by=['Country_Code', 'DateTime'], ignore_index=True)
	# create some new feature columns
	df['mt'] = 0.0
	df['Mt'] = 0.0
	df['pt'] = 0.0
	df['Pt'] = 0.0
	df['st'] = 0.0
	df['St'] = 0.0
	
	return df
	
	
def fill_missing_values(df) -> pd.DataFrame:
	"""Fill missing values with last known one (forward fill) and
	compute mobility features (mt, Mt, pt, Pt, st, St)
	
	Parameters
	----------
	df: DataFrame
		Data to process and finally returned
	
	Returns
	-------
	df: DataFrame
		Extended data
	"""
	for c_code in df['Country_Code'].unique():
		for col in COL.si_cols:
			# it does not fill zeros at the beginning
			filled_col = df.loc[(df.Country_Code == c_code)][col].replace(to_replace=0, method='ffill')
			df.loc[(df.Country_Code == c_code), col] = filled_col
		# some Countries missing values of confirmed cases, e.g. Aruba(ABW)
		filled_cases = df.loc[(df.Country_Code == c_code)]['ConfirmedCases'].replace(to_replace=0.0, method='ffill')
		df.loc[(df.Country_Code == c_code), 'ConfirmedCases'] = filled_cases
		
		filled_deaths = df.loc[(df.Country_Code == c_code)]['ConfirmedDeaths'].replace(to_replace=0.0, method='ffill')
		df.loc[(df.Country_Code == c_code), 'ConfirmedDeaths'] = filled_deaths
		
		filled_recovered = df.loc[(df.Country_Code == c_code)]['Recovered'].replace(to_replace=0.0, method='ffill')
		df.loc[(df.Country_Code == c_code), 'Recovered'] = filled_recovered
		
		stringency = df.loc[(df.Country_Code == c_code)]['StringencyIndex'].replace(to_replace=0.0, method='ffill')
		df.loc[(df.Country_Code == c_code), 'StringencyIndex'] = stringency
		
		# compute m(t|L)
		df.loc[(df.Country_Code == c_code), 'pt'] = df.loc[(df.Country_Code == c_code)][COL.si_cols].sum(axis=1) / 9
		df.loc[(df.Country_Code == c_code), 'Pt'] = df.loc[(df.Country_Code == c_code)]['pt'].cumsum()
		df.loc[(df.Country_Code == c_code), 'mt'] = 1 - df.loc[(df.Country_Code == c_code)]['pt']
		df.loc[(df.Country_Code == c_code), 'Mt'] = df.loc[(df.Country_Code == c_code)]['mt'].cumsum()
		df.loc[(df.Country_Code == c_code), 'st'] = df.loc[(df.Country_Code == c_code)]['StringencyIndex'] / 100
		df.loc[(df.Country_Code == c_code), 'St'] = df.loc[(df.Country_Code == c_code)]['st'].cumsum()
		
	return df


def transform_to_mobility(df, old_df, column, has_flag=True) -> pd.DataFrame:
	"""Transform the given Oxford Indicator values for S1 to S9
	to our model that describes the mobility of the population
	of a country.
	
	Parameters:
	-----------
	data : DataFrame object
	column : str
			column name of dataframe
	has_flag : bool
			Denotes weather a lockdown is general or just in some area
			Note: S8 doesn't use the regional reach (targeted
			or general).
			
	Returns:
	--------
	data : DataFrame object
	"""
	s_id = column.split('_')[0]
	if s_id == 'H1':
		idx = 9
	else:
		idx = int(s_id[1:])
	
	m_id = 'S' + str(idx)
	# set initial values
	si = old_df[column].copy()
	
	# set Si general initially to 1
	# because C8 needs a multiplication by 1
	si_g = old_df[column] * 0.0 + 1
	if has_flag:
		si_g = old_df[s_id + '_Flag']
	
	# general scope weight
	w = 0.28375
	# normalization factor
	nf = 1  # / 9
	
	if idx in [3, 5, 7, 9]:
		l_i = nf * (si / 2 * (1 - w) + (w * si_g))
	elif idx in [1, 2, 6]:
		l_i = nf * (si / 3 * (1 - w) + (w * si_g))
	elif idx in [4]:  # C_4
		l_i = nf * (si / 4 * (1 - w) + (w * si_g))
	elif idx in [8]:
		l_i = nf * si / 4  # C8
	else:
		l_i = 0.0
	
	df[m_id] = 0.0
	df[m_id] = l_i
	
	return df


def add_world_population_data(df) -> pd.DataFrame:
	"""Add information about the population in a country.
	
	Parameters
	----------
	df: DataFrame
	
	Returns
	-------
	df: DataFrame
	"""
	print("Add World Data...")
	wp = WorldPopulationData()
	df = df.merge(wp.df, left_on="Country_Code", right_on="Code", how="left")
	# clean some column names
	del df["CountryName_y"]
	del df["Code"]
	df = df.rename(columns={"CountryName_x": "CountryName"})
	print("- shape", df.shape)
	
	return df


def create_features(df) -> pd.DataFrame:
	"""Create additional features like active cases, relative
	cases (percentage of number of population) and daily cases.
	
	Parameters
	----------
	df: DataFrame

	Returns
	-------
	df: DataFrame
	"""
	print("Create Features...")
	df["Active"] = df.ConfirmedCases - df.ConfirmedDeaths - df.Recovered
	
	df['RelativeConfirmedCases'] = df.ConfirmedCases / df.Population
	df['RelativeConfirmedDeaths'] = df.ConfirmedDeaths / df.Population
	df["RelativeRecovered"] = df.Recovered / df.Population
	df["RelativeActive"] = df.Active / df.Population
	
	df['DailyConfirmedCases'] = 0
	df['DailyConfirmedDeaths'] = 0
	df["DailyRecovered"] = 0
	df["DailyActive"] = 0
	
	df['DaysCountFromFirstCase'] = 0
	
	for c in df.Country_Code.unique():
		dates = df.loc[(df.Country_Code == c) & (df.ConfirmedCases > 0)]['DateTime']
		days_count = dates - dates.min()
		
		df.loc[(df.Country_Code == c) & (
			df.ConfirmedCases > 0), 'DaysCountFromFirstCase'] = days_count.dt.days.values
		
		df.loc[(df.Country_Code == c), 'DailyConfirmedCases'] = df.loc[
			(df.Country_Code == c), 'ConfirmedCases'].diff()
		
		df.loc[(df.Country_Code == c), 'DailyConfirmedDeaths'] = df.loc[
			(df.Country_Code == c), 'ConfirmedDeaths'].diff()
		
		df.loc[(df.Country_Code == c), 'DailyRecovered'] = df.loc[
			(df.Country_Code == c), 'Recovered'].diff()
		
		df.loc[(df.Country_Code == c), 'DailyActive'] = df.loc[
			(df.Country_Code == c), 'Active'].diff()
	
	# replace the starting values that are set to Nan with 0
	df['DailyConfirmedCases'].fillna(0, inplace=True)
	df['DailyConfirmedDeaths'].fillna(0, inplace=True)
	df['DailyRecovered'].fillna(0, inplace=True)
	df['DailyActive'].fillna(0, inplace=True)
	
	print("- shape", df.shape)
		
	return df
