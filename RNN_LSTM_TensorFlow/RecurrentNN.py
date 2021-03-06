# -*- coding:utf-8 -*-
# Anaconda 5.0.1 環境 (TensorFlow インストール済み)

"""
    更新情報
    [17/11/29] : 新規作成
    [xx/xx/xx] : 

"""

import numpy

# TensorFlow ライブラリ
import tensorflow as tf
from tensorflow.python.framework import ops

# scikit-learn ライブラリ
from sklearn.utils import shuffle

# 自作クラス
from NeuralNetworkBase import NeuralNetworkBase    # 親クラス

import NNActivation
from NNActivation import NNActivation               # ニューラルネットワークの活性化関数を表すクラス
from NNActivation import Sigmoid
from NNActivation import Relu
from NNActivation import Softmax

import NNLoss                                       # ニューラルネットワークの損失関数を表すクラス
from NNLoss import L1Norm
from NNLoss import L2Norm
from NNLoss import BinaryCrossEntropy
from NNLoss import CrossEntropy
from NNLoss import SoftmaxCrossEntropy
from NNLoss import SparseSoftmaxCrossEntropy

import NNOptimizer                                  # ニューラルネットワークの最適化アルゴリズム Optimizer を表すクラス
from NNOptimizer import GradientDecent
from NNOptimizer import Momentum
from NNOptimizer import NesterovMomentum
from NNOptimizer import Adagrad
from NNOptimizer import Adadelta
from NNOptimizer import Adam


class RecurrentNN( NeuralNetworkBase ):
    """
    リカレントニューラルネットワーク [RNN : Recurrent Neural Network] を表すクラス.
    TensorFlow での RNN の処理をクラス（任意の層に DNN 化可能な柔軟なクラス）でラッピングし、
    scikit-learn ライブラリの classifier, estimator とインターフェイスを共通化することで、
    scikit-learn ライブラリとの互換性のある自作クラス
    ------------------------------------------------------------------------------------------------
    [public] public アクセス可能なインスタスンス変数には, 便宜上変数名の最後にアンダースコア _ を付ける.
        _n_inputLayer : int
            入力層のノード数
        _n_hiddenLayer : int
            隠れ層のノード数
        _n_outputLayer : int
            出力層のノード数

        _n_in_sequence : int
            時系列データを区切った各シークエンスの長さ（サイズ）

        _rnn_cells : list<BasicRNNCell クラスのオブジェクト> <tensorflow.python.ops.rnn_cell_impl.BasicRNNCell>
            RNN 構造を提供する cell のリスト
            この `cell` は、内部（プロパティ）で state（隠れ層の状態）を保持しており、
            これを次の時間の隠れ層に順々に渡していくことで、時間軸の逆伝搬を実現する。
        _rnn_states : list<Tensor>
            cell の状態
            
        _weights : list <Variable>
            モデルの各層の重みの Variable からなる list
        _biases : list <Variable>
            モデルの各層のバイアス項の  Variable からなる list

        _epochs : int
            エポック数（トレーニング回数）
        _batch_size : int
            ミニバッチ学習でのバッチサイズ
        _eval_step : int
            学習処理時に評価指数の算出処理を行う step 間隔

        _losses_train : list <float32>
            トレーニングデータでの損失関数の値の list

        _X_holder : placeholder
            入力層にデータを供給するための placeholder
        _t_holder : placeholder
            出力層に教師データを供給するための placeholder
        _keep_prob_holder : placeholder
            ドロップアウトしない確率 (1-p) にデータを供給するための placeholder
        _batch_size_holder : placeholder
            バッチサイズ _batch_size にデータを供給するための placeholder
            cell.zero_state(...) でバッチサイズを指定する必要があり、可変長に対応するために必要

    [protedted] protedted な使用法を想定 


    [private] 変数名の前にダブルアンダースコア __ を付ける（Pythonルール）


    """
    def __init__( 
            self,
            session = tf.Session( config = tf.ConfigProto(log_device_placement=True) ),
            n_inputLayer = 1, n_hiddenLayer = 1, n_outputLayer = 1, 
            n_in_sequence = 25,
            epochs = 1000,
            batch_size = 10,
            eval_step = 1
        ):
        """
        コンストラクタ（厳密にはイニシャライザ）
        """
        super().__init__( session )

        tf.set_random_seed(12)

        # 各パラメータの初期化
        self._n_inputLayer = n_inputLayer
        self._n_hiddenLayer = n_hiddenLayer
        self._n_outputLayer = n_outputLayer

        self._n_in_sequence = n_in_sequence

        self._rnn_cells = []
        self._rnn_states = []

        self._weights = []
        self._biases = []

        self._epochs = epochs
        self._batch_size = batch_size
        self._eval_step = eval_step        

        # evaluate 関連の初期化
        self._losses_train = []

        # placeholder の初期化
        # shape の列（横方向）は、各層の次元（ユニット数）に対応させる。
        # shape の行は、None にして汎用性を確保
        self._X_holder = tf.placeholder( 
                             tf.float32, 
                             shape = [ None, self._n_in_sequence, self._n_inputLayer ],
                             name = "X_holder"
                         )

        self._t_holder = tf.placeholder( 
                             tf.float32, 
                             shape = [ None, self._n_outputLayer ],
                             name = "t_holder"
                         )

        self._keep_prob_holder = tf.placeholder( tf.float32, name = "keep_prob_holder" )
        self._batch_size_holder = tf.placeholder( tf.int32, shape=[], name = "batch_size_holder" )

        return


    def print( self, str ):
        print( "----------------------------------" )
        print( str )
        print( self )

        print( "_session : ", self._session )
        print( "_init_var_op :\n", self._init_var_op )

        print( "_loss_op : ", self._loss_op )
        print( "_optimizer : ", self._optimizer )
        print( "_train_step : ", self._train_step )
        print( "_y_out_op : ", self._y_out_op )

        print( "_n_inputLayer : ", self._n_inputLayer )
        print( "_n_hiddenLayer : ", self._n_hiddenLayer )
        print( "_n_outputLayer : ", self._n_outputLayer )

        print( "_n_in_sequence : ", self._n_in_sequence )

        print( "_epoches : ", self._epochs )
        print( "_batch_size : ", self._batch_size )
        print( "_eval_step : ", self._eval_step )

        print( "_X_holder : ", self._X_holder )
        print( "_t_holder : ", self._t_holder )
        print( "_keep_prob_holder : ", self._keep_prob_holder )
        print( "_batch_size_holder : ", self._batch_size_holder )

        print( "_rnn_cells : \n", self._rnn_cells )
        #if( (self._session != None) and (self._init_var_op != None) ):
            #print( self._session.run( self._rnn_cells ) )

        print( "_rnn_states : \n", self._rnn_states )
        #if( (self._session != None) and (self._init_var_op != None) ):
            #print( self._session.run( self._rnn_states ) )

        print( "_weights : \n", self._weights )
        if( (self._session != None) and (self._init_var_op != None) ):
            print( self._session.run( self._weights ) )

        print( "_biases : \n", self._biases )
        if( (self._session != None) and (self._init_var_op != None) ):
            print( self._session.run( self._biases ) )

        print( "----------------------------------" )
        return


    def init_weight_variable( self, input_shape ):
        """
        重みの初期化を行う。
        重みは TensorFlow の Variable で定義することで、
        学習過程（最適化アルゴリズム Optimizer の session.run(...)）で自動的に TensorFlow により、変更される値となる。

        [Input]
            input_shape : [int,int]
                重みの Variable を初期化するための Tensor の形状

        [Output]
            正規分布に基づく乱数で初期化された重みの Variable 
            session.run(...) はされていない状態。
        """

        # ゼロで初期化すると、うまく重みの更新が出来ないので、正規分布に基づく乱数で初期化
        # tf.truncated_normal(...) : Tensor を正規分布なランダム値で初期化する
        init_tsr = tf.truncated_normal( shape = input_shape, stddev = 0.01 )

        # 重みの Variable
        weight_var = tf.Variable( init_tsr, name = "init_weight_var" )
        
        return weight_var


    def init_bias_variable( self, input_shape ):
        """
        バイアス項 b の初期化を行う。
        バイアス項は TensorFlow の Variable で定義することで、
        学習過程（最適化アルゴリズム Optimizer の session.run(...)）で自動的に TensorFlow により、変更される値となる。

        [Input]
            input_shape : [int,int]
                バイアス項の Variable を初期化するための Tensor の形状

        [Output]
            ゼロ初期化された重みの Variable 
            session.run(...) はされていない状態。
        """

        #init_tsr = tf.zeros( shape = input_shape )
        init_tsr = tf.random_normal( shape = input_shape )

        # バイアス項の Variable
        bias_var = tf.Variable( init_tsr, name = "init_bias_var" )

        return bias_var


    def model( self ):
        """
        モデルの定義（計算グラフの構築）を行い、
        最終的なモデルの出力のオペレーターを設定する。

        [Output]
            self._y_out_op : Operator
                モデルの出力のオペレーター
        """
        #--------------------------------------------------------------
        # 入力層 ~ 隠れ層
        #--------------------------------------------------------------
        # tf.contrib.rnn.BasicRNNCell(...) : 時系列に沿った RNN 構造を提供するクラス `BasicRNNCell` のオブジェクト cell を返す。
        # この cell は、内部（プロパティ）で state（隠れ層の状態）を保持しており、
        # これを次の時間の隠れ層に順々に渡していくことで、時間軸の逆伝搬を実現する。
        cell = tf.contrib.rnn.BasicRNNCell( 
                   num_units = self._n_hiddenLayer     # int, The number of units in the RNN cell.
                   #activation = "tanh"                  # Nonlinearity to use. Default: tanh
               )
        #print( "cell :", cell )

        # 最初の時間 t0 では、過去の隠れ層がないので、
        # cell.zero_state(...) でゼロの状態を初期設定する。
        initial_state_tsr = cell.zero_state( self._batch_size_holder, tf.float32 )
        #print( "initial_state_tsr :", initial_state_tsr )

        #-----------------------------------------------------------------
        # 過去の隠れ層の再帰処理
        #-----------------------------------------------------------------
        self._rnn_states.append( initial_state_tsr )

        with tf.variable_scope('RNN'):
            for t in range( self._n_in_sequence ):
                if (t > 0):
                    # tf.get_variable_scope() : 名前空間を設定した Variable にアクセス
                    # reuse_variables() : reuse フラグを True にすることで、再利用できるようになる。
                    tf.get_variable_scope().reuse_variables()

                # BasicRNNCellクラスの `__call__(...)` を順次呼び出し、
                # 各時刻 t における出力 cell_output, 及び状態 state を算出
                cell_output, state_tsr = cell( inputs = self._X_holder[:, t, :], state = self._rnn_states[-1] )

                # 過去の隠れ層の出力をリストに追加
                self._rnn_cells.append( cell_output )
                self._rnn_states.append( state_tsr )

        # 最終的な隠れ層の出力
        output = self._rnn_cells[-1]

        # 隠れ層 ~ 出力層
        self._weights.append( self.init_weight_variable( input_shape = [self._n_hiddenLayer, self._n_outputLayer] ) )
        self._biases.append( self.init_bias_variable( input_shape = [self._n_outputLayer] ) )

        #--------------------------------------------------------------
        # 出力層への入力
        #--------------------------------------------------------------
        y_in_op = tf.matmul( output, self._weights[-1] ) + self._biases[-1]

        #--------------------------------------------------------------
        # モデルの出力
        #--------------------------------------------------------------
        # 線形活性
        self._y_out_op = y_in_op

        return self._y_out_op


    def loss( self, nnLoss ):
        """
        損失関数の定義を行う。
        
        [Input]
            nnLoss : NNLoss クラスのオブジェクト
            
        [Output]
            self._loss_op : Operator
                損失関数を表すオペレーター
        """
        self._loss_op = nnLoss.loss( t_holder = self._t_holder, y_out_op = self._y_out_op )
        
        return self._loss_op


    def optimizer( self, nnOptimizer ):
        """
        モデルの最適化アルゴリズムの設定を行う。

        [Input]
            nnOptimizer : NNOptimizer のクラスのオブジェクト

        [Output]
            optimizer の train_step
        """
        self._optimizer = nnOptimizer._optimizer
        self._train_step = nnOptimizer.train_step( self._loss_op )
        
        return self._train_step


    def fit( self, X_train, y_train ):
        """
        指定されたトレーニングデータで、モデルの fitting 処理を行う。

        [Input]
            X_train : numpy.ndarray ( shape = [n_samples, n_features] )
                トレーニングデータ（特徴行列）
            
            y_train : numpy.ndarray ( shape = [n_samples] )
                トレーニングデータ用のクラスラベル（教師データ）のリスト

        [Output]
            self : 自身のオブジェクト
        """
        #----------------------------
        # 学習開始処理
        #----------------------------
        # Variable の初期化オペレーター
        self._init_var_op = tf.global_variables_initializer()

        # Session の run（初期化オペレーター）
        self._session.run( self._init_var_op )

        #-------------------
        # 学習処理
        #-------------------
        # for ループでエポック数分トレーニング
        for epoch in range( self._epochs ):
            # ミニバッチ学習処理のためランダムサンプリング
            idx_shuffled = numpy.random.choice( len(X_train), size = self._batch_size )
            X_train_shuffled = X_train[ idx_shuffled ]
            y_train_shuffled = y_train[ idx_shuffled ]

            #print( "X_train_shuffled.shape", X_train_shuffled.shape )
            #print( "y_train_shuffled.shape", y_train_shuffled.shape )
            #print( "X_train_shuffled.shape", X_train_shuffled.shape )

            # 設定された最適化アルゴリズム Optimizer でトレーニング処理を run
            self._session.run(
                self._train_step,
                feed_dict = {
                    self._X_holder: X_train_shuffled,
                    self._t_holder: y_train_shuffled,
                    self._batch_size_holder: self._batch_size
                }
            )
            
            # 評価処理を行う loop か否か
            # % : 割り算の余りが 0 で判断
            if ( ( (epoch+1) % self._eval_step ) == 0 ):
                # 損失関数値の算出
                loss = self._loss_op.eval(
                       session = self._session,
                       feed_dict = {
                           self._X_holder: X_train_shuffled,
                           self._t_holder: y_train_shuffled,
                           self._batch_size_holder: self._batch_size
                       }
                   )

                self._losses_train.append( loss )
                print( "epoch %d / loss = %f" % ( epoch, loss ) )

        return self._y_out_op


    def predict( self, X_test ):
        """
        fitting 処理したモデルで、推定を行い、時系列データの予想値を返す。

        [Input]
            X_test : numpy.ndarry ( shape = [n_samples, n_features(=n_in_sequence), dim] )
                予想したい特徴行列（時系列データの行列）
                n_samples : シーケンスに分割した時系列データのサンプル数
                n_features(=n_in_sequence) : １つのシーケンスのサイズ
                dim : 各シーケンスの要素の次元数

        [Output]
            predicts : numpy.ndarry ( shape = [n_samples] )
                予想結果（分類モデルの場合は、クラスラベル）
        """
        # 元データの最初の一部 τ 文（１シーケンス）だけを切り出し、
        # 後に、τ+1 を予想 → τ+2 を予想 ...
        X_t = X_test[:1]    # X(t=1) ~ X(t=τ)

        # 予想値のリスト（時系列データ）
        # t=1～τ までの予想値はないので None とする。
        predicts = [ None for i in range(self._n_in_sequence) ]
        
        # 指定した時系列データの総数(t) / t は シーケンス数 t-τ+1 の t 項に対応した値
        if ( X_test.ndim >= 2):
            # 入力層の数が１ノード（入力データの特徴量が１種類）
            if ( self._n_inputLayer == 1 ):
                n_sequences = len( X_test[:,0] ) + len( X_test[0,:] ) - 1
            # 入力層の数が複数ノード（入力データの特徴量が複数個）
            elif( self._n_inputLayer >= 2 ):
                n_sequences = ( len( X_test[:,0] ) + len( X_test[0,:] ) ) * self._n_inputLayer - 1
            else:
                n_sequences = len( X_test[:,0] ) + len( X_test[0,:] ) - 1
        else:
            n_sequences = len( X_test ) - 1

        print( "n_sequences :", n_sequences )

        # サイズが τ で、
        # { f(t=1), f(t=2), ... , f(t=τ) }, { f(t=2), f(t=3), ... , f(t=τ+1) }, ... , { f(t-τ), f(t-τ+1), ... , f(t) }
        #  の合計 t - τ + 1 個のデータセットに対応したループ処理
        # n_sequences - self._n_in_sequence + 1 : 時系列データの総数(t) - シーケンス内のデータ数(τ) + 1 
        for i in range( n_sequences - self._n_in_sequence + 1):
            # 最後の時系列データを抽出
            # ２回目以降のループでは、new_sequence
            X_t_last = X_t[-1:]

            # 最後の時系列データ X_t_last から未来 prob を予測
            prob = self._session.run(
                       self._y_out_op,
                       feed_dict = { 
                           self._X_holder: X_t_last,
                           self._batch_size_holder: 1
                       }
                   )
            #print( "prob :", prob )

            # ? 予測結果 prob を用いて新しい時系列データ new_sequence を生成
            # numpy.concatenate(...) : ２個以上の配列を軸指定して結合 / axis : 0
            # x_last + prob
            # X_t_last.reshape(self._n_in_sequence, self._n_inputLayer)[1:] : 
            # shape = [25,1] に reshape し、[1:] で2番目~最後のシーケンス（各々サイズ _n_in_sequence のベクトル）指定
            """
            new_sequence = numpy.concatenate(
                               ( X_t_last.reshape(self._n_in_sequence, self._n_inputLayer)[1:], prob ), axis = 0
                           ).reshape( 1, self._n_in_sequence, self._n_inputLayer )
            """
            #print( "new_sequence.shape :", new_sequence.shape )
            #print( "new_sequence :", new_sequence )

            new_sequence = X_t_last.reshape(self._n_in_sequence, self._n_inputLayer)[:]
            #print( "X_t_last.reshape(self._n_in_sequence, self._n_inputLayer)[:] :", new_sequence )    # [signal, mask] / shape = (249, 2)
            new_sequence = numpy.concatenate( new_sequence, axis = 0 )
            #print( "numpy.concatenate( new_sequence, axis = 0 ) :", new_sequence )                      # [signal[0]], [mask[0]], ... / shape = (498,)
            new_sequence = new_sequence.reshape( 1, self._n_in_sequence, self._n_inputLayer )
            #print( "numpy.concatenate( new_sequence, axis = 0 ) :", new_sequence )

            # new_sequence を append した新たな X_t とする。
            X_t = numpy.append( X_t, new_sequence, axis = 0 )
            
            # prob[0][0] : prob = [[xxx]] を shape=1 に reshape し
            # array(xxx, dtype=float32) の値 xxx を格納
            predicts.append( prob[0][0] )
        
        return predicts


    def predict_proba( self, X_test ):
        """
        fitting 処理したモデルで、推定を行い、クラスの所属確率の予想値を返す。
        proba : probability

        [Input]
            X_test : numpy.ndarry ( shape = [n_samples, n_features] )
                予想したい特徴行列
        """
        prob = self._y_out_op.eval(
                   session = self._session,
                   feed_dict = {
                       self._X_holder: X_test 
                   }
               )
        
        return prob


    def accuracy( self, X_test, y_test ):
        """
        指定したデータでの正解率 [accuracy] を計算する。
        """
        # 予想ラベルを算出する。
        predict = self.predict( X_test )

        # 正解数
        n_correct = numpy.sum( numpy.equal( predict, y_test ) )
        #print( "numpy.equal( predict, y_test ) :", numpy.equal( predict, y_test ) )
        #print( "n_correct :", n_correct )

        # 正解率 = 正解数 / データ数
        accuracy = n_correct / X_test.shape[0]

        return accuracy

    def accuracy_labels( self, X_test, y_test ):
        """
        指定したデータでのラベル毎の正解率 [acuuracy] を算出する。
        """
        # 予想ラベルを算出する。
        predict = self.predict( X_test )

        # ラベル毎の正解率のリスト
        n_labels = len( numpy.unique( y_test ) )    # ユニークな要素数
        accuracys = []

        for label in range(n_labels):
            # label 値に対応する正解数
            # where(...) : 条件を満たす要素番号を抽出
            n_correct = len( numpy.where( predict == label )[0] )
            """
            n_correct = numpy.sum( 
                            numpy.equal( 
                                numpy.where( predict == label )[0], 
                                numpy.where( y_test == label )[0]
                            ) 
                        )
            """

            # サンプル数
            n_sample = len( numpy.where( y_test == label )[0] )

            accuracy = n_correct / n_sample
            accuracys.append( accuracy )
            
            #print( "numpy.where( predict == label ) :", numpy.where( predict == label ) )
            #print( "numpy.where( predict == label )[0] :", numpy.where( predict == label )[0] )
            print( " %d / n_correct = %d / n_sample = %d" % ( label, n_correct, n_sample ) )

        return accuracys

