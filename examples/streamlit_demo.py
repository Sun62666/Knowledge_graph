import streamlit as st
if __name__ == '__main__':
    st.title("我的第一个streamlit应用")
    st.header("我的第一个streamlit应用")
    st.write("Hello!World!")
    st.success("✅ 成功")
    st.info("ℹ️ 信息")
    st.warning("⚠️ 警告")
    st.error("❌ 错误")
    st.code("print('hello')",language="python")
    st.write("=======================================================")

    name = st.text_input("请输入名字",placeholder="怨天")
    age = st.number_input("年龄",min_value=0,max_value=120,value=20)
    city = st.selectbox("选择城市",["北京","成都"])
    hobbies = st.multiselect("兴趣爱好",["读书","运动","钓鱼"])
    score = st.slider("评分",0,100,50)
    date = st.date_input("选择日期")
    uploaded_file = st.file_uploader("上传文件",type=["csv","txt"])
    st.write("=======================================================")

    if st.button("点击我"):
        st.write("按钮被点击了！")
    if st.button("提交",type="primary"):
        st.success("提交成功")
    if st.checkbox("显示信息"):
        st.write("这是详细信息")
    option = st.radio("选择性别",["男","女"])
    st.write("=======================================================")

    col1,col2,col3 = st.columns(3)
    with col1:
        st.write("第一列")
    with col2:
        st.write("第二列")
    with col3:
        st.write("第三列")

    with st.sidebar:
        st.title("侧边栏")
        option = st.selectbox("菜单",["选项1","选项2"])
    with st.expander("查看更多"):
        st.write("隐藏的内容")
    tab1,tab2 = st.tabs(["标签1","标签2"])
    with tab1:
        st.write("标签1内容")
    with tab2:
        st.write("标签2内容")
    st.write("=======================================================")

    import pandas as pd
    df = pd.DataFrame(
        {
            "姓名": ["张三", "李四", "王五"],
            "年龄": [25, 30, 35],
            "城市": ["北京", "上海", "广州"]
        }
    )
    st.dataframe(df)
    st.table(df)

    st.line_chart(df["年龄"])
    st.bar_chart(df["年龄"])
    st.area_chart(df["年龄"])

    st.metric(label="总用户数",value="1.234",delta="+12%")
    st.write("=======================================================")

    st.image("photo.png",caption="照片",width=300)
    # st.video("video.mp4")
    # st.audio("music.mp3")
    st.write("=======================================================")


    import time
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.1)
        progress_bar.progress(i+1)
    with st.spinner("正在处理..."):
        time.sleep(2)
    st.success("完成！")
    st.balloons()

    st.title("性能测试")
    @st.cache_data
    def expensive_task():
        time.sleep(2)
        return "计算完成"
    if st.button("惦记我"):
        result = expensive_task()
        st.write(result)