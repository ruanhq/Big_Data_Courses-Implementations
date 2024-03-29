####
import pyspark
from pyspark import SparkConf, SparkContext


statCharacterID = 5306
targetCharacterID = 14

hitCounter = sc.accumulator(0)


def convertToBFS(line):
	fields = line.split()
	heroID = int(fields[0])
	connections = []
	for connection in fields[1:]:
		connections.append(int(connection))
	####
	color = 'WHITE'
	distance = 9999
	###
	if (heroID == startCharacterID):
		color = 'GRAY'
	distance = 0
	###
	return (heroID, (connections, distance, color))

#####
#RDD: Resilient distributed dataset, immutable, partitioned collection of elements that can be ran in parallel.
#Properties:
#1. List of Partitions.
#2. Function for computing each split
#3. List of dependencies on other RDDs
#4. Optionally, a list of preferred locations to compute each split on:

from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.sql.functions import mean,col,split, col, regexp_extract, when, lit
from pyspark.ml.feature import StringIndexer
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import QuantileDiscretizer
import pyspark
import os
import sys
os.chdir('/Users/ruanhq/Desktop/Spark/data')
os.environ['SPARK_HOME'] = '/Users/ruanhq/Desktop/Spark/spark-2.4.3-bin-hadoop2.7'
SPARK_HOME =os.environ['SPARK_HOME']
sys.path.insert(0, os.path.join(SPARK_HOME, 'python'))
sys.path.insert(0, os.path.join(SPARK_HOME, 'python','lib'))
sys.path.insert(0, os.path.join(SPARK_HOME, 'python', 'lib', 'pyspark.zip'))
sys.path.insert(0, os.path.join(SPARK_HOME, 'python', 'lib', 'py4j-0.10.7-src.zip'))


from pyspark.sql import SparkSession
from pyspark import SparkContext

#Starting a spark session:
spark = SparkSession \
.builder \
.master('local[2]')\
.appName('ruanhqspark')\
.config('spark.executor.memory', '1g')\
.config('spark.cores.max', '2')\
.config('spark.sql.warehouse.dir', '/Users/ruanhq/Spark/spark-warehouse').getOrCreate()

SpContext = SpSession.sparkContext

titanic_df = spark.read.csv('train.csv', header = 'True', inferSchema = 'True')
passengers_count = titanic_df.count()
titanic_df.show(5)
titanic_df.describe().show()

#####
#
titanic_df.printSchema()
#
titanic_df.select('Survived', 'Pclass', 'Embarked').show()

titanic_df.groupBy('Survived').count().show()
titanic_df.groupBy('Pclass', 'Survived', 'Embarked').count().show()


#####checking null values:
def null_value_count(df):
	null_columns_counts = []
	numRows = df.count()
	for k in df.columns:
		#Number of missing values:
		nullRows = df.where(col(k).isNull()).count()
		if(nullRows > 0):
			temp = k, nullRows
			null_columns_counts.append(temp)
	return(null_columns_counts)

null_value_count(titanic_df)

#####
#specify the columns:
spark.createDataFrame(null_value_count(titanic_df), ['Column_with_null_value', 'Null_values_count']).show()
mean_age = titanic_df.select(mean('Age')).collect()[0][0]

#####
#Create another column:
titanic_df = titanic_df.withColumn('Initial', regexp_extract(col('Name'), '([A-Za-z]+)\.', 1))

titanic_df.select('Initial').distinct().show()
##replace,
# withColumn, select,
# createDataFrame, groupBy, 
#printSchema, sparkContext, 
#collect(), filter
#when(Condition1, 0).otherwise(columns)
titanic_df = titanic_df.replace(['Mlle','Mme', 'Ms', 'Dr','Major','Lady','Countess','Jonkheer','Col','Rev','Capt','Sir','Don'],
               ['Miss','Miss','Miss','Mr','Mr',  'Mrs',  'Mrs',  'Other',  'Other','Other','Mr','Mr','Mr'])


titanic_df.groupby('Initial').avg('Age').collect()

#Perform another training model:
titanic_df = titanic_df.withColumn("Age",when((titanic_df["Initial"] == "Miss") & (titanic_df["Age"].isNull()), 22).otherwise(titanic_df["Age"]))
titanic_df = titanic_df.withColumn("Age",when((titanic_df["Initial"] == "Other") & (titanic_df["Age"].isNull()), 46).otherwise(titanic_df["Age"]))
titanic_df = titanic_df.withColumn("Age",when((titanic_df["Initial"] == "Master") & (titanic_df["Age"].isNull()), 5).otherwise(titanic_df["Age"]))
titanic_df = titanic_df.withColumn("Age",when((titanic_df["Initial"] == "Mr") & (titanic_df["Age"].isNull()), 33).otherwise(titanic_df["Age"]))
titanic_df = titanic_df.withColumn("Age",when((titanic_df["Initial"] == "Mrs") & (titanic_df["Age"].isNull()), 36).otherwise(titanic_df["Age"]))

#Check the imputation:
titanic_df.filter(titanic_df.Age == 46).select('Initial').show()
titanic_df.select('Age').show()
titanic_df.groupBy('Embarked').count().show()

#Fill the NA:
titanic_df = titanic_df.na.fill({'Embarked': 'S'})
titanic_df = titanic_df.drop('Cabin')
titanic_df = titanic_df.withColumn('Family_Size', col('SibSp') + col('Parch'))
titanic_df.groupBy('Family_Size').count().show()

titanic_df = titanic_df.withColumn('Alone', lit(0))
titanic_df = titanic_df.withColumn('Alone', when(titanic_df['Family_Size'] == 0, 1).otherwise(titanic_df['Alone']))
#####
#Transform, estimator, pipeline.
#pipeline.fit().transform()
#label encoding:
indexes = [StringIndexer(inputCol = column, outputCol = column + '_index').fit(titanic_df) for column in ['Sex', 'Embarked', 'Initial']]
pipeline = Pipeline(stages = indexes)
titanic_df = pipeline.fit(titanic_df).transform(titanic_df)
titanic_df.show(3)

titanic_df = titanic_df.drop('PassengerId', 'Name', 'Ticket', 'Cabin', 'Embarked', 'Sex', 'Initial')
titanic_df.show(5)

feature = VectorAssembler(inputCols=titanic_df.columns[1:],outputCol="features")
feature_vector= feature.transform(titanic_df)
feature_vector.show(5)
#Run a simple Naive Bayes algorithm:
#split the training and test set:
(trainingData, testData) = feature_vector.randomSplit([0.8, 0.2],seed = 11)
from pyspark.ml.classification import LogisticRegression
lr = LogisticRegression(labelCol = 'Survived', featuresCol = 'features')
lr_model = lr.fit(training_data)
lr_prediction = lr_model.transform(test_data)
lr_prediction.select('prediction', 'Survived', 'features').show()
#Performing the ml tuning:
evaluator = MulticlassClassificationEvaluator(labelCol = 'Survived',)





#Performing feature engineering by apache spark:
from pyspark.sql.functions import avg

bureau = spark.read.csv('bureau.csv', header = 'True', inferSchema = 'True')
#display(bureau.where('SK_ID_CURR = 100001'))

bureau.printSchema()
bureau_10000 = bureau.limit(10000)
loans_per_customer = bureau_10000.select('SK_ID_CURR', 'DAYS_CREDIT').groupBy('SK_ID_CURR').count().withColumnRenamed("count", "BUREAU_LOAN_COUNT")
bureau_10000 = bureau_10000.join(loans_per_customer, ['SK_ID_CURR'], how = 'left')
print((bureau_10000.count(), len(bureau_10000.columns)))
#display(bureau_10000)
#Number of types of past loans:
loans_type_per_customer = 









########
#Using spark to perform the nlp task:
from pyspark.ml import Pipeline 
from pyspark.ml.feature import CountVectorizer, StringIndexer, RegexTokenizer, StopWordsRemover
from pyspark.sql.functions import col, udf, regexp_replace, isnull
from pyspark.sql.types import StringType, IntegerType
from pyspark.ml.classification import 
from pyspark.ml.evaluation import MulticlassClassificationEvaluator


news_data = spark.read.csv('uci-news-aggregator.csv', header = 'True', inferSchema = 'True')
news_data.count()

def null_value_count(df):
	null_columns_counts = []
	numRows = df.count()
	for k in df.columns:
		nullRows = df.where(col(k).isNull()).count()
		if(nullRows > 0):
			temp = k, nullRows
			null_columns_count.append(temp)
	return null_value_count

#createDataFrame!
missing_count = spark.createDataFrame(null_value_count(news_data), ['Coulmn_with_Null_Value', 'Null_values_count']).show()
#
title_category = news_data.select('TITLE', 'CATEGORY')

title_category.select('Category').distinct().count()
title_category.groupBy('Category').count().orderBy(col('Count').desc()).show(truncate = False)
title_category.groupBy('TITLE').count().orderBy(col('count').desc()).show(truncate = False)
####
#Top 20 news categories:
#regexp_replace: regular expression replacing!
title_category = title_category.withColumn('only_str', regexp_replace(col('TITLE'), '\d+', ''))
title_category.select('TITLE', 'only_str').show(truncate = False)

#Top 20 news title:
regex_tokenizer = RegexTokenizer(inputCol = 'only_str', outputCol = 'words', pattern = '\\W')
raw_words = regex_tokenizer.transform(title_category)
raw_words.show()


remover = StopWordsRemover(inputCol = 'words', outputCol = 'filtered')
word_df = remover.transform(raw_words)
word_df.select('words', 'filtered').show(truncate = False)
indexer = StringIndexer(inputCol = 'CATEGORY', outputCol = 'categoryIndex')
feature_data = indexer.fit(word_df).transform(word_df)
feature_data.show()


cv = CountVectorizer(inputCol = 'filtered', outputCol = 'features')




