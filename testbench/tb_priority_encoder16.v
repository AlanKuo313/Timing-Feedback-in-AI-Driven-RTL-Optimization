`timescale 1ns/1ps
module tb_priority_encoder16;
    reg clk=0;
    always #5 clk=~clk;
    reg [15:0] req=0, prev_req=0;
    wire valid;
    wire [3:0] index;
    reg exp_valid;
    reg [3:0] exp_index;
    integer cycle=0, k, i;
    priority_encoder16 dut(.clk(clk), .req(req), .valid(valid), .index(index));
    always @(posedge clk) begin
        if(cycle>0) begin
            exp_valid = (prev_req != 0);
            exp_index = 0;
            for(i=0;i<16;i=i+1) if(prev_req[i]) exp_index=i;
            #1;
            if(valid !== exp_valid || index !== exp_index) $fatal(1,"priority mismatch cycle %0d",cycle);
        end
        prev_req=req; cycle=cycle+1;
    end
    initial begin
        for(k=0;k<250;k=k+1) begin
            @(negedge clk);
            req=(k%5==0)?16'b0:$random;
        end
        @(negedge clk);
        $display("PASS: priority_encoder16 %0d vectors",cycle-1);
        $finish;
    end
endmodule
