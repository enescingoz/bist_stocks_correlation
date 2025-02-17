import config

import yfinance
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sb
from datetime import datetime, timedelta
from timeit import default_timer as timer 



def date_string_to_datetime(date_string):
	return datetime.strptime(date_string, "%Y-%m-%d")


def get_next_day_string(current_day_string):
	current_day_datetime = date_string_to_datetime(current_day_string)
	next_day_datetime = current_day_datetime + timedelta(days=1)
	next_day_string = next_day_datetime.strftime("%Y-%m-%d")
	return next_day_string


def date_range(start_datetime, end_datetime):
    for i in range(int((end_datetime - start_datetime).days) + 1):
        yield start_datetime + timedelta(i)


def fill_missing_data(df, start_time, end_time):
	start_datetime = date_string_to_datetime(start_time)
	end_datetime = date_string_to_datetime(end_time)
	df_new = df[0:0]
	dates_list = [str(datetime)[:10] for datetime in date_range(start_datetime, end_datetime)]
	datetimes_list = [datetime for datetime in date_range(start_datetime, end_datetime)]
	dates_index = 0
	first_df_row_value = df.iloc[0, 1]
	while dates_list[dates_index] < str(df.iloc[0, 0])[:10]:
		new_row = pd.DataFrame({"Date": [datetimes_list[dates_index]],
								"Value": [first_df_row_value]})
		df_new = pd.concat([df_new, new_row], axis=0, ignore_index=True)
		dates_index += 1
	last_dates_index = dates_index
	df_index = 0
	for dates_index in range(last_dates_index, len(dates_list)):
		if df_index < df.shape[0] and str(df.iloc[df_index, 0])[:10] == dates_list[dates_index]:
			new_row = pd.DataFrame({"Date": [df.iloc[df_index, 0]],
									"Value": [df.iloc[df_index, 1]]})
			df_new = pd.concat([df_new, new_row], axis=0, ignore_index=True)
			last_new_row_value = df.iloc[df_index, 1]
			df_index += 1
		elif df_index >= df.shape[0] or str(df.iloc[df_index, 0])[:10] > dates_list[dates_index]:
			new_row = pd.DataFrame({"Date": [datetimes_list[dates_index]],
									"Value": [last_new_row_value]})
			df_new = pd.concat([df_new, new_row], axis=0, ignore_index=True)
			if df_index >= df.shape[0]:
				print("WARNING: Missing data added to the end of the downloaded dataframe. Date:", datetimes_list[dates_index])
	return df_new


def remove_extra_data(df, start_time, end_time):
	rows_to_be_removed = []
	for index, row in df.iterrows():
		if str(row["Date"])[:10] < start_time or str(row["Date"])[:10] > end_time:
			rows_to_be_removed.append(index)
	df = df.drop(rows_to_be_removed)
	return df


def get_data_for_pair_name(pair_name, column_name, data_source, start_time, end_time):
	
	if data_source == "yfinance":
		df = yfinance.download(pair_name, start=get_next_day_string(start_time), end=get_next_day_string(end_time), interval="1d", auto_adjust=True, prepost=True, threads=True)
	df = df.reset_index()
	df = df[['Date', column_name]]
	df = df.rename(columns={column_name: "Value"})
	return df


def get_values_list_from_dataframe(df):
	return df["Value"].tolist()


def get_values_for_pair_names_list(pair_names_with_column_name_list, start_time, end_time):
	all_pair_names_values_list = []
	for pair_name, column_name, data_source in pair_names_with_column_name_list:
		try:
			print("Quote:", pair_name, "(" + str(column_name) + ", " + str(data_source) + ")")
			df = get_data_for_pair_name(pair_name, column_name, data_source, start_time, end_time)
			print("Data downloaded")
			df = remove_extra_data(df, start_time, end_time)
			print("Extra data removed")
			df = fill_missing_data(df, start_time, end_time)
			print("Missing data filled")
			values_list = get_values_list_from_dataframe(df)
			print("_" * 80)
			all_pair_names_values_list.append(values_list)
		except Exception as e:
			print(f"An error occurred: {e}")
            
	return all_pair_names_values_list


def generate_matrix_from_all_pair_names_values(all_pair_names_values_list, pair_names_list):
	df = pd.DataFrame(all_pair_names_values_list)
	df = df.T
	columns_rename_dict = {}
	for i in range(len(pair_names_list)):
		columns_rename_dict[i] = pair_names_list[i][0].split('/')[-1]
	df = df.rename(columns=columns_rename_dict)
	df = df.corr()
	return df


def concat_datasets(dataset1, dataset2):
	ret = []
	for row in dataset1:
		ret.append(row)
	for row in dataset2:
		ret.append(row)
	return ret


def generate_correlation_matrix(pair_names_list, start_time, end_time, output_csv_file_path, output_csv_file_delimiter, threshold):
	timer_start = timer()
	all_pair_names_values_list = get_values_for_pair_names_list(pair_names_list, start_time, end_time)
	df = generate_matrix_from_all_pair_names_values(all_pair_names_values_list, pair_names_list)

	

	##### APPLY THRESHOLD FOR CORRELATION VALUE
	filtered_df = df.where(df > threshold)


	##### CREATE PAIRS OF MOST CORRELATED STOCKS
	# Create a set to keep track of pairs
	seen_pairs = set()

	# Create a list to store the results
	results = []

	# Iterate over the DataFrame to collect the values that meet the threshold and sort descending order
	for i in filtered_df.index:
		for j in filtered_df.columns:
			try:
				value = filtered_df.at[i, j]
				if pd.notna(value) and value > threshold and i != j:
					# Sort the pair to avoid duplicates
					pair = tuple(sorted([i, j]))
					if pair not in seen_pairs:
						seen_pairs.add(pair)
						results.append((i, j, value))
			except Exception as e:
				print(f"[ERROR]: {e}")
	sorted_results = sorted(results, key=lambda x: x[2], reverse=True)

	# Convert the list to a DataFrame
	result_df = pd.DataFrame(sorted_results, columns=["Stock", "Correlated_Stock", "Correlation_Value"])

	# Display the new DataFrame
	print(result_df)

	print("_" * 80)
	filtered_df.to_csv(output_csv_file_path, sep=output_csv_file_delimiter)
	result_df.to_csv("correlated_pairs.csv", sep=output_csv_file_delimiter)

	print("Runtime:", timer()-timer_start)
	sb.heatmap(filtered_df, annot=True)
	plt.show()



def main():
	END_TIME = datetime.now().strftime('%Y-%m-%d')
	generate_correlation_matrix(config.PAIR_NAMES_LIST_WITH_SOURCE,
					 			config.START_TIME,
					 			END_TIME,
								config.OUTPUT_CSV_FILE_PATH,
								config.OUTPUT_CSV_FILE_DELIMITER,
								config.CORRELATION_THRESHOLD)


if __name__ == "__main__":
	main()
