from flask import Flask, request, render_template, redirect, url_for
from flask import send_from_directory, make_response, flash, send_file
from werkzeug.utils import secure_filename
import os
from io import BytesIO
import pandas as pd 
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import chi2, f_regression
import seaborn as sns
import numpy as np 
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure



app = Flask(__name__)
app.config.update(
	TESTING=True,
	SECRET_KEY =b'\x0e$+\xdd\xc0\x041\xba\xec\x1d^T9%\xe9\x8d'
	)


ALLOWED_EXTENSIONS = set(['xls','xlsx','csv'])

def allowed_file(filename):
	# checks if extension is valid
	return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def label_to_int(file_df):
	# finds unique string labels and turns them to integers
	for col,dtype in file_df.dtypes.iteritems():
		if dtype == object:
			dict = {}
			labels = file_df[col].unique()
			for i in range(len(labels)):
				dict[labels[i]] = i+1
			file_df[col] = [dict[item] for item in file_df[col]]
			print(dict)
	return file_df


@app.route('/')
def homepage():
	return render_template('homepage.html')

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():

	global secure_file,result

	if request.method == 'POST':
		result = request.form['radios']
		result = str(result)
		if 'file' not in request.files:
			return redirect(request.url)
		file = request.files['file']

		if file.filename == '':
			return redirect(request.url)

		if file and allowed_file(file.filename):
			secure_file = secure_filename(file.filename)
			f_path = os.path.join(app.root_path, secure_file)
			file.save(f_path)

			return redirect(url_for('redir'))
		else:
			return render_template('homepage.html')
	else:
		return render_template('homepage.html')

	 

@app.route('/upload_redirect', methods=['GET', 'POST'])
def redir():

	global secure_file, secured_file
	secured_file = secure_file

	if 'xls' in secured_file:
		file_df = pd.read_excel(os.path.join(app.root_path, secured_file))
		secured_file = secured_file.rsplit('.',1)[0]  # get 'filename without .csv or .xls'
		file_df.to_csv(os.path.join(app.root_path, secured_file, '.csv'), encoding='utf-8', index=False)
		
	file_df = pd.read_csv(os.path.join(app.root_path, secured_file))
	file_df = label_to_int(file_df)
	column_names = list(file_df)
	file_df.to_csv(os.path.join(app.root_path, secured_file), encoding='utf-8', index=False)
		
	return render_template('output_choice.html', columns=column_names)



@app.route('/problem_type', methods=['GET','POST'])
def problem_type():

	global result, secured_file

	input_columns = request.form.getlist('input_choice')
	output_column = str(request.form['output_choice'])

	file_df = pd.read_csv(os.path.join(app.root_path, secured_file))
	keep_columns = input_columns + [output_column]
	file_df = file_df[keep_columns]
	file_df.to_csv(os.path.join(app.root_path, secured_file), encoding='utf-8', index=False)

	return render_template('analysis_options.html', input_col=input_columns, out_col=output_column, type=result)


@app.route('/redir_method', methods=['GET','POST'])
def chosen_method():

	if request.method == 'POST':
		choice = request.form['cust_select']
		choice = str(choice)
		if choice == "select":
			return redirect(request.url)

		return redirect(url_for(choice))


@app.route('/bestfeatures')
def bestfeatures():
	global secured_file, result

	file_df = pd.read_csv(os.path.join(app.root_path, secured_file))
	X = file_df.iloc[:,0:-1]
	y = file_df.iloc[:,-1]
	num_of_feat = len(list(X))

	if result == 'regression':
		bestfeatures = SelectKBest(score_func=f_regression, k=num_of_feat) #regression
	else:
		bestfeatures = SelectKBest(score_func=chi2, k=num_of_feat) #classification

	fit = bestfeatures.fit(X,y)
	dfscores = pd.DataFrame(fit.scores_)
	dfcolumns = pd.DataFrame(X.columns)
	featureScores = pd.concat([dfcolumns, dfscores],axis=1)
	featureScores.columns = ['Specs', 'Score']
	feat_score = featureScores.nlargest(3, 'Score')
	feat_score = feat_score.to_html(escape=False)

	return render_template("dataframe_example.html", html_data=feat_score)


@app.route('/correlation.png', methods=['GET', 'POST'])
def correlation():

	global secured_file
	
	file_df = pd.read_csv(os.path.join(app.root_path, secured_file))
	corrmat = file_df.corr()
	top_corr_features = corrmat.index
	print(top_corr_features)

	sns.heatmap(file_df[top_corr_features].corr(), annot=True, cmap="RdYlGn")
	fig = plt.figure(figsize=(20,20))
	sns.heatmap(file_df[top_corr_features].corr(), annot=True, cmap="RdYlGn")
	canvas = FigureCanvas(fig)
	img = BytesIO()
	fig.savefig(img)
	img.seek(0)
	return send_file(img, mimetype='image/png')


if __name__ == '__main__':
	app.run(debug=True)
