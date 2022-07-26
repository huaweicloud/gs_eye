[�ű�����]

gs_metric.py    ��ؽű����壬Ϊ���ڵ����У��ɶԲ���ϵͳ��Gauss���ݿ�ָ����м��
gs_metric.sh    ��gs_metric.py�ű��ķ�װ�����ڼ�Ⱥ���ű��Ĺ���

gs_archive.py   �������ű����壬��Ϊ����ˣ���ʱ�������ݣ���������ά����


---------------------------------------------------------------------------------------
gs_metric.py

[����˵��]

1.   -i, --indir         ָ�����������Ŀ¼;
2.   -o, --outdir        ָ����־���·��;
3.   -u, --username      ���ݿ��û���;
4.   -w, --password      �û����룬Ĭ��Ϊ�գ����»���"omm"�û�����ָ��;
5.   --logsize           ��������־��С��Ĭ��1024����λΪMB;
6.   --logtime           ��������־ʱ����Ĭ�������ƣ���λΪ��;
7.   --url               ����˵�URL�����ڽ�����־�ļ���Ĭ��Ϊ�գ���ʾ������;
8.   --interval          ������־�ļ���ʱ������Ĭ��30����λΪ��;
9.   -h, --help          ��ʾ������Ϣ;
10.  -v, --version       ��ʾ�汾��;


[�÷�����]

���»���ʹ��omm�û�������ʹ��Ruby�û���source����������ִ��;

1. ��ӿ�ִ��Ȩ��
chmod +x gs_metric.py

2. �ű�����
./gs_metric.py -i metric_item/ -o /tmp/ -u omm &

3. ������������
./gs_metric.py -i metric_item/ -o /tmp/ -u omm --logsize=300 --logtime=7 &
./gs_metric.py -i metric_item/ -o /tmp/ -u omm --url=127.0.0.1/metric --interval=10


[���˵��]

1.  gs_metric-xxxx-xx-xx_xxxxxx.log     �ű�������־����¼�ű�����״��
2.  database/cn_xxxx/xxxx               ��ʵ���¸��������
3.  system/xxxx                         ����ϵͳ��Դ���ؽ��
4.  metric_item/metric_item.conf        ����ָ�����ű������ָ��Ŀ¼�Զ����ɼ�������ļ�


[ע��]

��ؽű������ָ��Ŀ¼������xxxx.sh��cn_xxxx.sql��dn_xxxx.sql�ļ���������ִ��;


---------------------------------------------------------------------------------------
gs_metric.sh

[����˵��]

1.   start           ������Ⱥ��أ�����Ӷ�ʱ����;
2.   stop            ֹͣ��Ⱥ��أ����Ƴ���ʱ����;
3.   status          ��⼯Ⱥ�ڸ��ڵ��ؽű�������״̬;
4.   version         ��ʾ�汾��;
5.   help            ��ʾ������Ϣ;

ʹ��ǰ���޸���Ӧ�Ļ���������
1.   MET_HOME="${GAUSSHOME}/bin/dfx_tool/gs_metric"       ���߹���Ŀ¼������·��;
2.   BIN_HOME="${MET_HOME}/bin"                           gs_metric.py�ű�����Ŀ¼��Ĭ�ϲ���;
3.   MET_BIN="gs_metric.py"                               ��ؽű����ƣ�Ĭ�ϲ���;
3.   ITEM_HOME="${MET_HOME}/metric_item"                  ������ļ�����Ŀ¼��Ĭ�ϲ���;
3.   LOG_HOME="${GAUSSLOG}"                               �������־�ļ�����Ŀ¼;
4.   MET_OPT="-u omm"                                     ������gs_metric.py���������磺-u omm -w Gauss_234��;
5.   START_HOME="${MET_HOME}"                             gs_metric.sh�ű�����Ŀ¼��Ĭ�ϲ���;
7.   START_BIN="gs_metric.sh"                             ����ű����ƣ�Ĭ�ϲ���;


[�÷�����]

1. ��ӿ�ִ��Ȩ��
chmod +x gs_metric.sh

2. �ű�����
./gs_metric.sh start

3. �ű�ֹͣ
./gs_metric.sh stop

4. ���״̬
./gs_metric.sh status

5. ��ʾ�汾
./gs_metric.sh version

6. ��ʾ����
./gs_metric.sh help


[���˵��]

���н����������


[ע��]

start���ܽ��ڸ��ڵ���Ӷ�ʱ���񣬽ű�������Ҫ1��������


---------------------------------------------------------------------------------------
gs_archive.py

[����˵��]

1.   -o, --outdir        ָ����־���·��;
2.   -d, --database      ��ά�����ƣ�Ĭ��Ϊ: "gsmetric";
3.   -u, --username      ���ݿ��û���;
4.   -w, --password      �û����룬Ĭ��Ϊ�գ����»���"omm"�û�����ָ��;
5.   --datatime          ��ά�Ᵽ������ʱ����Ĭ��30����λΪ��;
6.   --interval          ��������ʱ������Ĭ��30����λΪ��;
7.   --logsize           ��������־��С��Ĭ��1024����λΪMB;
8.   --logtime           ��������־ʱ����Ĭ�������ƣ���λΪ��;
9.   -h, --help          ��ʾ������Ϣ;
10.  -v, --version       ��ʾ�汾��;


[�÷�����]

���»���ʹ��omm�û�������ʹ��Ruby�û���source����������ִ��;
gs_archive.py������8.1�����°汾������ʹ��python2;

1. ��ӿ�ִ��Ȩ��
chmod +x gs_archive.py

2. �ű�����
./gs_archive.py -o /tmp/ -u omm &

3. ������������
./gs_metric.py -o /tmp/ -u omm --datatime=30 --logsize=300 &


[���˵��]

1. gs_archive-xxxx-xx-xx_xxxxxx.log        �ű�������־����¼�ű�����״��
2. gs_archive_dump-xxxx-xx-xx_xxxxxx       ������������־����¼�����ϸ����
